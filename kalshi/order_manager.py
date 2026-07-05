"""Order placement, fill handling, and stop-loss management."""

import logging
import threading
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from config.settings import get_settings
from kalshi.rest_client import KalshiRestClient
from storage.trade_log import TradeLog

logger = logging.getLogger(__name__)


def _fmt_decimal(value: Decimal | float | str) -> str:
    d = Decimal(str(value))
    quantized = d.quantize(Decimal("0.0001"))
    return f"{quantized:.4f}"


def _fmt_count(value: Decimal | float | str) -> str:
    d = Decimal(str(value))
    quantized = d.quantize(Decimal("0.01"))
    return f"{quantized:.2f}"


@dataclass
class EntryState:
    client_order_id: str
    ticker: str
    asset: str
    side: str  # "bid" (buy YES) or "ask" (sell YES = long NO)
    entry_price: Decimal
    requested_count: Decimal
    filled_count: Decimal = Decimal("0")
    remaining_count: Decimal = Decimal("0")
    stop_width: Decimal = Decimal("0.15")
    order_id: str | None = None
    stop_order_id: str | None = None
    stop_client_order_id: str | None = None
    stop_order_id_2: str | None = None  # Second dual stop for redundancy
    stop_client_order_id_2: str | None = None
    tp_order_id: str | None = None
    tp_client_order_id: str | None = None
    tp_price: Decimal | None = None
    tp_filled: bool = False


class OrderManager:
    """Manages entries, fills, and IoC aggressive stop-losses."""

    def __init__(self, rest: KalshiRestClient, trade_log: TradeLog | None = None):
        self.rest = rest
        self.trade_log = trade_log or TradeLog()
        self.entries: dict[str, EntryState] = {}  # client_order_id -> EntryState
        self.order_id_to_client: dict[
            str, str
        ] = {}  # server order_id -> client_order_id
        self.settled_tickers: set[str] = set()
        self.entry_order_ids: set[str] = set()  # track all entry order_ids
        self.stop_order_ids: set[str] = set()  # track all stop order_ids
        self.tp_order_ids: set[str] = set()  # track all take-profit order_ids
        self.stop_to_parent_entry_price: dict[
            str, Decimal
        ] = {}  # stop_order_id -> entry_price
        self.settings = get_settings()
        self._lock = threading.Lock()  # Protect shared state from concurrent access

    # ------------------------------------------------------------------
    # Entry placement
    # ------------------------------------------------------------------

    def place_entry(
        self,
        ticker: str,
        asset: str,
        side: str,
        price: Decimal,
        count: Decimal,
        stop_width: Decimal = Decimal("0.15"),
    ) -> EntryState:
        """Place a single entry order and return its state."""
        client_order_id = str(uuid.uuid4())
        payload = {
            "ticker": ticker,
            "side": side,
            "count": _fmt_count(count),
            "price": _fmt_decimal(price),
            "time_in_force": "good_till_canceled",
            "self_trade_prevention_type": "taker_at_cross",
            "client_order_id": client_order_id,
            "post_only": True,
        }

        response = self.rest.post("/portfolio/events/orders", json_data=payload)
        order_id = response.get("order_id")

        entry = EntryState(
            client_order_id=client_order_id,
            ticker=ticker,
            asset=asset,
            side=side,
            entry_price=price,
            requested_count=count,
            remaining_count=count,
            stop_width=stop_width,
            order_id=order_id,
        )
        with self._lock:
            self.entries[client_order_id] = entry
            if order_id:
                self.order_id_to_client[order_id] = client_order_id
                self.entry_order_ids.add(order_id)

        self.trade_log.log_event(
            "entry_placed",
            {
                "asset": asset,
                "ticker": ticker,
                "side": side,
                "price": str(price),
                "count": str(count),
                "client_order_id": client_order_id,
                "order_id": order_id,
            },
        )
        logger.info(
            "Placed entry %s %s %s @ %s (%s contracts)",
            asset,
            side,
            ticker,
            price,
            count,
        )
        return entry

    # ------------------------------------------------------------------
    # Fill handling
    # ------------------------------------------------------------------

    def on_entry_fill(
        self,
        order_id: str | None,
        client_order_id: str | None,
        fill_price: str,
        fill_count: str,
        fill_side: str = "maker",
    ) -> None:
        """Handle an entry fill event. Place IoC stop for newly filled count."""
        client_order_id = self._resolve_client_id(order_id, client_order_id)
        if not client_order_id or client_order_id not in self.entries:
            logger.warning(
                "Fill for unknown entry order: order_id=%s client=%s",
                order_id,
                client_order_id,
            )
            return

        with self._lock:
            entry = self.entries[client_order_id]
            entry.filled_count += Decimal(fill_count)
            entry.remaining_count = max(
                Decimal("0"), entry.requested_count - entry.filled_count
            )

        self.trade_log.log_event(
            "fill",
            {
                "asset": entry.asset,
                "ticker": entry.ticker,
                "side": entry.side,
                "fill_price": fill_price,
                "fill_count": fill_count,
                "fill_side": fill_side,
                "total_filled": str(entry.filled_count),
                "client_order_id": client_order_id,
                "order_id": order_id,
                "entry_price": str(entry.entry_price),
            },
        )

        if entry.filled_count > Decimal("0"):
            self._place_stop_order(entry)
            self._place_take_profit_order(entry)

    def on_stop_fill(
        self,
        order_id: str | None,
        client_order_id: str | None,
        fill_price: str,
        fill_count: str,
        fill_side: str = "taker",
    ) -> None:
        """Handle a stop fill event. Cancels other dual stop and take-profit."""
        asset = "unknown"
        ticker = "unknown"
        side = "unknown"
        parent_entry_client_order_id = None
        entry_price = None
        matched_entry = None

        with self._lock:
            # Find entry by either stop client_order_id (primary or secondary)
            for entry in self.entries.values():
                if (
                    entry.stop_client_order_id == client_order_id
                    or entry.stop_client_order_id_2 == client_order_id
                ):
                    asset = entry.asset
                    ticker = entry.ticker
                    side = entry.side
                    parent_entry_client_order_id = entry.client_order_id
                    entry_price = self.stop_to_parent_entry_price.get(order_id)
                    matched_entry = entry
                    break

        if entry_price is None:
            logger.warning(
                "Stop fill received but no parent entry price found for order_id=%s",
                order_id,
            )
            entry_price_str = "0.0000"
        else:
            entry_price_str = str(entry_price)

        # Cancel the OTHER dual stop and take-profit (outside lock to avoid blocking)
        if matched_entry:
            self._cancel_dual_stops(matched_entry)
            # Cancel take-profit if still active
            if matched_entry.tp_order_id and not matched_entry.tp_filled:
                self._cancel_order(
                    matched_entry.tp_order_id, matched_entry.tp_client_order_id
                )
                with self._lock:
                    self.tp_order_ids.discard(matched_entry.tp_order_id)
                    self.order_id_to_client.pop(matched_entry.tp_order_id, None)
                    matched_entry.tp_order_id = None
                    matched_entry.tp_client_order_id = None
                    matched_entry.tp_filled = True
                logger.info("Cancelled take-profit for %s after stop fill", asset)

        self.trade_log.log_event(
            "stop_fill",
            {
                "asset": asset,
                "ticker": ticker,
                "side": side,
                "fill_price": fill_price,
                "fill_count": fill_count,
                "fill_side": fill_side,
                "order_id": order_id,
                "client_order_id": client_order_id,
                "parent_entry_client_order_id": parent_entry_client_order_id,
                "entry_price": entry_price_str,
            },
        )
        logger.info(
            "Stop filled: %s %s %s contracts @ %s (side=%s)",
            asset,
            ticker,
            fill_count,
            fill_price,
            fill_side,
        )

    def on_tp_fill(
        self,
        order_id: str | None,
        client_order_id: str | None,
        fill_price: str,
        fill_count: str,
        fill_side: str = "taker",
    ) -> None:
        """Handle a take-profit fill event."""
        asset = "unknown"
        ticker = "unknown"
        side = "unknown"
        parent_entry_client_order_id = None

        with self._lock:
            for entry in self.entries.values():
                if entry.tp_client_order_id == client_order_id:
                    asset = entry.asset
                    ticker = entry.ticker
                    side = entry.side
                    parent_entry_client_order_id = entry.client_order_id
                    entry.tp_filled = True
                    break

        self.trade_log.log_event(
            "take_profit_fill",
            {
                "asset": asset,
                "ticker": ticker,
                "side": side,
                "fill_price": fill_price,
                "fill_count": fill_count,
                "fill_side": fill_side,
                "order_id": order_id,
                "client_order_id": client_order_id,
                "parent_entry_client_order_id": parent_entry_client_order_id,
            },
        )
        logger.info(
            "Take-profit filled: %s %s %s contracts @ %s",
            asset,
            ticker,
            fill_count,
            fill_price,
        )

    # ------------------------------------------------------------------
    # Stop placement
    # ------------------------------------------------------------------

    def _stop_side(self, entry: EntryState) -> str:
        """Return the side needed to flatten the entry."""
        return "ask" if entry.side == "bid" else "bid"

    def _stop_price(self, entry: EntryState) -> Decimal:
        """Compute primary stop price level relative to entry price.

        YES long (bid entry):  sell stop at entry_price - stop_width
        NO long (ask entry):   buy stop at entry_price + stop_width

        Example with entry ~$0.50 and stop_width=$0.15:
          YES primary stop at $0.35, NO primary stop at $0.65
        """
        if entry.side == "bid":
            return max(Decimal("0.01"), entry.entry_price - entry.stop_width)
        else:
            return min(Decimal("0.99"), entry.entry_price + entry.stop_width)

    def _stop_price_2(self, entry: EntryState) -> Decimal:
        """Compute secondary stop price level (2¢ closer to entry price
        than primary, making it the first line of defense).

        YES long (bid entry):  sell stop at primary + 0.02
        NO long (ask entry):   buy stop at primary - 0.02
        """
        if entry.side == "bid":
            return min(
                entry.entry_price,
                self._stop_price(entry) + Decimal("0.02"),
            )
        else:
            return max(
                entry.entry_price,
                self._stop_price(entry) - Decimal("0.02"),
            )

    def _take_profit_price(self, entry: EntryState) -> Decimal:
        """Compute take-profit price for the entry.

        For a long YES position: sell at 0.98 (just below $1.00)
        For a long NO position: buy at 0.02 (just above $0.00)
        """
        if entry.side == "bid":
            # Long YES: sell to lock profit at 0.98
            return Decimal("0.98")
        else:
            # Long NO: buy YES back at 0.02 (market YES goes to $0, we win)
            return Decimal("0.02")

    def _place_take_profit_order(self, entry: EntryState) -> None:
        """Place a take-profit order to lock in profits."""
        if entry.filled_count <= Decimal("0") or entry.tp_filled:
            return

        # Cancel existing TP if any
        if entry.tp_order_id:
            self._cancel_order(entry.tp_order_id, entry.tp_client_order_id)
            with self._lock:
                self.order_id_to_client.pop(entry.tp_order_id, None)
                self.stop_order_ids.discard(entry.tp_order_id)

        # Take-profit side is OPPOSITE of entry
        # If we bought YES (bid), we sell YES (ask) to take profit
        tp_side = "ask" if entry.side == "bid" else "bid"
        tp_price = self._take_profit_price(entry)
        count = entry.filled_count
        client_order_id = str(uuid.uuid4())

        payload = {
            "ticker": entry.ticker,
            "side": tp_side,
            "count": _fmt_count(count),
            "price": _fmt_decimal(tp_price),
            "time_in_force": "good_till_canceled",
            "self_trade_prevention_type": "taker_at_cross",
            "client_order_id": client_order_id,
            "post_only": True,
            "reduce_only": True,
        }

        try:
            response = self.rest.post("/portfolio/events/orders", json_data=payload)
            entry.tp_order_id = response.get("order_id")
            entry.tp_client_order_id = client_order_id
            entry.tp_price = tp_price
            status = response.get("status", "")

            if not entry.tp_order_id or status in ("canceled", "rejected"):
                logger.warning(
                    "Take-profit FAILED for %s %s — continuing without TP. Entry price: %s",
                    entry.asset,
                    entry.ticker,
                    entry.entry_price,
                )
                entry.tp_order_id = None
                return

            with self._lock:
                self.order_id_to_client[entry.tp_order_id] = client_order_id
                self.tp_order_ids.add(entry.tp_order_id)

            filled = Decimal(str(response.get("fill_count", "0")))
            remaining = count - filled

            self.trade_log.log_event(
                "take_profit_placed",
                {
                    "asset": entry.asset,
                    "ticker": entry.ticker,
                    "side": tp_side,
                    "price": str(tp_price),
                    "count": str(count),
                    "client_order_id": client_order_id,
                    "order_id": entry.tp_order_id,
                    "filled_count": str(filled),
                    "remaining_count": str(remaining),
                },
            )
            logger.info(
                "Placed take-profit %s %s @ %s (%s contracts, filled %s, remaining %s)",
                entry.asset,
                entry.ticker,
                tp_price,
                count,
                filled,
                remaining,
            )

            if remaining > Decimal("0"):
                logger.info(
                    "Take-profit partial fill for %s %s — %s remaining unfilled",
                    entry.asset,
                    entry.ticker,
                    remaining,
                )

        except Exception:
            logger.exception("Failed to place take-profit for %s", entry.asset)

    def _place_stop_order(self, entry: EntryState) -> None:
        """Place dual limit stop-loss orders first (to avoid taker fees).

        Places two stops at different price levels:
        - Primary stop: entry_price +/- stop_width
        - Secondary stop: slightly tighter (entry_price +/- stop_width +/- 0.02)
        When either fills, the other is cancelled.
        """
        if entry.filled_count <= Decimal("0"):
            return

        # Cancel any existing dual stops before placing new ones
        self._cancel_dual_stops(entry)

        side = self._stop_side(entry)
        count = entry.filled_count

        # Primary stop (farther from entry)
        price_1 = self._stop_price(entry)
        client_id_1 = str(uuid.uuid4())

        # Secondary stop (closer to entry)
        price_2 = self._stop_price_2(entry)
        client_id_2 = str(uuid.uuid4())

        # Place primary stop
        self._place_single_limit_stop(entry, side, price_1, client_id_1, "primary")
        # Place secondary stop
        self._place_single_limit_stop(entry, side, price_2, client_id_2, "secondary")

    def _place_single_limit_stop(
        self, entry: EntryState, side: str, price: Decimal, client_id: str, label: str
    ) -> None:
        """Place a single limit stop order."""
        count = entry.filled_count

        payload = {
            "ticker": entry.ticker,
            "side": side,
            "count": _fmt_count(count),
            "price": _fmt_decimal(price),
            "time_in_force": "good_till_canceled",
            "self_trade_prevention_type": "taker_at_cross",
            "client_order_id": client_id,
            "post_only": True,
            "reduce_only": True,
        }

        try:
            response = self.rest.post("/portfolio/events/orders", json_data=payload)
            order_id = response.get("order_id")
            status = response.get("status", "")

            if not order_id or status in ("canceled", "rejected"):
                logger.warning(
                    "Limit stop (%s) not posted for %s %s at %s — will retry as IOC",
                    label,
                    entry.asset,
                    entry.ticker,
                    price,
                )
                self._place_single_ioc_stop(entry, side, price, client_id, label)
                return

            # Track which stop this is (primary or secondary)
            with self._lock:
                if label == "primary":
                    entry.stop_order_id = order_id
                    entry.stop_client_order_id = client_id
                else:
                    entry.stop_order_id_2 = order_id
                    entry.stop_client_order_id_2 = client_id
                self.order_id_to_client[order_id] = client_id
                self.stop_order_ids.add(order_id)

            self.trade_log.log_event(
                "stop_placed",
                {
                    "asset": entry.asset,
                    "ticker": entry.ticker,
                    "side": side,
                    "price": str(price),
                    "count": str(count),
                    "client_order_id": client_id,
                    "order_id": order_id,
                    "type": "limit_maker",
                    "label": label,
                    "entry_price": str(entry.entry_price),
                },
            )
            logger.info(
                "Placed limit stop (%s) %s %s @ %s (%s contracts)",
                label,
                entry.asset,
                entry.ticker,
                price,
                count,
            )

        except Exception:
            logger.exception(
                "Failed to place stop order (%s) for %s", label, entry.asset
            )

    def _place_single_ioc_stop(
        self, entry: EntryState, side: str, price: Decimal, client_id: str, label: str
    ) -> None:
        """Place a single IOC stop order."""
        count = entry.filled_count

        payload = {
            "ticker": entry.ticker,
            "side": side,
            "count": _fmt_count(count),
            "price": _fmt_decimal(price),
            "time_in_force": "immediate_or_cancel",
            "self_trade_prevention_type": "taker_at_cross",
            "client_order_id": client_id,
            "reduce_only": True,
        }

        try:
            response = self.rest.post("/portfolio/events/orders", json_data=payload)
            order_id = response.get("order_id")

            with self._lock:
                if label == "primary":
                    entry.stop_order_id = order_id
                    entry.stop_client_order_id = client_id
                else:
                    entry.stop_order_id_2 = order_id
                    entry.stop_client_order_id_2 = client_id
                self.order_id_to_client[order_id] = client_id
                self.stop_order_ids.add(order_id)

            logger.info(
                "Placed IOC stop (%s) %s %s @ %s (as fallback)",
                label,
                entry.asset,
                entry.ticker,
                price,
            )
        except Exception:
            logger.exception("Failed to place IOC stop (%s) for %s", label, entry.asset)

    def _cancel_dual_stops(self, entry: EntryState) -> None:
        """Cancel both dual stop orders for an entry."""
        if entry.stop_order_id:
            self._cancel_order(entry.stop_order_id, entry.stop_client_order_id)
            with self._lock:
                self.order_id_to_client.pop(entry.stop_order_id, None)
                self.stop_order_ids.discard(entry.stop_order_id)
            entry.stop_order_id = None
            entry.stop_client_order_id = None

        if entry.stop_order_id_2:
            self._cancel_order(entry.stop_order_id_2, entry.stop_client_order_id_2)
            with self._lock:
                self.order_id_to_client.pop(entry.stop_order_id_2, None)
                self.stop_order_ids.discard(entry.stop_order_id_2)
            entry.stop_order_id_2 = None
            entry.stop_client_order_id_2 = None

    def check_stop_escalation(self, ticker: str, market_price: float) -> None:
        """Check if market has passed stop levels. Only escalates to IOC when
        BOTH limit-stops are bypassed (market gapped through both without fill).

        Dual-stop ladder (example for long YES at $0.50, stop_width=$0.15):
          Secondary stop at $0.37 — first defense, closer to entry
          Primary stop at $0.35   — last resort

        If only the secondary is passed, we cancel the stale secondary limit
        and rely on the primary.  Only when market passes the primary AND the
        secondary was already bypassed (or both are still active) do we escalate
        to an aggressive IOC to flatten the position.
        """
        market_price = Decimal(str(market_price))

        with self._lock:
            for entry in list(self.entries.values()):
                if entry.ticker != ticker:
                    continue
                if entry.filled_count <= Decimal("0"):
                    continue

                primary_stop = self._stop_price(entry)
                secondary_stop = self._stop_price_2(entry)
                secondary_bypassed = False

                if entry.side == "bid":
                    # Long YES: sell stops below entry price
                    # Secondary ($0.37) is closer to entry — cancel if bypassed but
                    # don't escalate yet; primary ($0.35) may still catch it.
                    if market_price <= secondary_stop and entry.stop_order_id_2:
                        logger.warning(
                            "Secondary stop bypassed for %s (mkt=%s <= sec=%s) — "
                            "canceling stale limit, relying on primary at %s",
                            entry.asset,
                            market_price,
                            secondary_stop,
                            primary_stop,
                        )
                        self._cancel_order(
                            entry.stop_order_id_2, entry.stop_client_order_id_2
                        )
                        with self._lock:
                            self.order_id_to_client.pop(entry.stop_order_id_2, None)
                            self.stop_order_ids.discard(entry.stop_order_id_2)
                            entry.stop_order_id_2 = None
                            entry.stop_client_order_id_2 = None
                        secondary_bypassed = True

                    # If market also passed (or is at) primary, BOTH are bypassed → IoC
                    if market_price <= primary_stop:
                        if entry.stop_order_id:
                            logger.warning(
                                "BOTH stops bypassed for %s (mkt=%s <= pri=%s) — escalating to IOC",
                                entry.asset,
                                market_price,
                                primary_stop,
                            )
                            self._escalate_to_ioc(entry)
                        elif secondary_bypassed:
                            logger.warning(
                                "BOTH stops bypassed for %s (secondary canceled, "
                                "primary gone) — escalating to IOC",
                                entry.asset,
                            )
                            self._escalate_to_ioc(entry)

                else:
                    # Long NO: buy stops above entry price (mirror logic)
                    if market_price >= secondary_stop and entry.stop_order_id_2:
                        logger.warning(
                            "Secondary stop bypassed for %s (mkt=%s >= sec=%s) — "
                            "canceling stale limit, relying on primary at %s",
                            entry.asset,
                            market_price,
                            secondary_stop,
                            primary_stop,
                        )
                        self._cancel_order(
                            entry.stop_order_id_2, entry.stop_client_order_id_2
                        )
                        with self._lock:
                            self.order_id_to_client.pop(entry.stop_order_id_2, None)
                            self.stop_order_ids.discard(entry.stop_order_id_2)
                            entry.stop_order_id_2 = None
                            entry.stop_client_order_id_2 = None
                        secondary_bypassed = True

                    if market_price >= primary_stop:
                        if entry.stop_order_id:
                            logger.warning(
                                "BOTH stops bypassed for %s (mkt=%s >= pri=%s) — escalating to IOC",
                                entry.asset,
                                market_price,
                                primary_stop,
                            )
                            self._escalate_to_ioc(entry)
                        elif secondary_bypassed:
                            logger.warning(
                                "BOTH stops bypassed for %s (secondary canceled, "
                                "primary gone) — escalating to IOC",
                                entry.asset,
                            )
                            self._escalate_to_ioc(entry)

    def _escalate_to_ioc(self, entry: EntryState) -> None:
        """Place an aggressive IOC stop as last resort when BOTH limit stops
        have been bypassed (market gapped through without filling either).

        Keeps the existing limit stops LIVE as a backup — if the market reverses
        they may catch the position at a better price.  Once the IOC fills,
        `on_stop_fill()` will clean up the limit stops and take-profit.
        """

        # Place IOC for full filled count
        side = self._stop_side(entry)
        price = self._stop_price(entry)
        count = entry.filled_count
        client_id = str(uuid.uuid4())

        payload = {
            "ticker": entry.ticker,
            "side": side,
            "count": _fmt_count(count),
            "price": _fmt_decimal(price),
            "time_in_force": "immediate_or_cancel",
            "self_trade_prevention_type": "taker_at_cross",
            "client_order_id": client_id,
            "reduce_only": True,
        }

        try:
            response = self.rest.post("/portfolio/events/orders", json_data=payload)
            order_id = response.get("order_id")

            with self._lock:
                entry.stop_order_id = order_id
                entry.stop_client_order_id = client_id
                self.order_id_to_client[order_id] = client_id
                self.stop_order_ids.add(order_id)

            self.trade_log.log_event(
                "stop_escalated_to_ioc",
                {
                    "asset": entry.asset,
                    "ticker": entry.ticker,
                    "price": str(price),
                    "count": str(count),
                },
            )
            logger.info(
                "Escalated to IOC stop %s %s @ %s (%s contracts)",
                entry.asset,
                entry.ticker,
                price,
                count,
            )
        except Exception:
            logger.exception(
                "Failed to place IOC stop for %s during escalation", entry.asset
            )

    def check_tp_proximity(self, ticker: str, market_price: float) -> None:
        """Log when price approaches take-profit level for any active entry.

        Logs once per proximity event (2¢ threshold) so logs don't spam
        during normal price noise.
        """
        market_price_dec = Decimal(str(market_price))
        proximity_threshold = Decimal("0.02")

        with self._lock:
            for entry in list(self.entries.values()):
                if entry.ticker != ticker:
                    continue
                if entry.filled_count <= Decimal("0") or entry.tp_filled:
                    continue
                if not entry.tp_price:
                    continue

                tp_price = entry.tp_price
                distance = abs(market_price_dec - tp_price)

                if distance <= proximity_threshold:
                    logger.info(
                        "TP in range for %s %s: mkt=%s tp=%s dist=%s",
                        entry.asset,
                        entry.ticker,
                        market_price_dec,
                        tp_price,
                        distance,
                    )

    def _emergency_cancel_entry(self, entry: EntryState) -> None:
        """Cancel the entry order if IoC stop fails, to limit further fill exposure."""
        if entry.order_id and entry.remaining_count > Decimal("0"):
            logger.warning(
                "Emergency canceling entry %s to prevent further fills", entry.asset
            )
            self._cancel_order(entry.order_id, entry.client_order_id)

    # ------------------------------------------------------------------
    # Settlement handling
    # ------------------------------------------------------------------

    def on_settlement(
        self, ticker: str, result: str, settlement_price: str | None
    ) -> None:
        """Mark a ticker as settled and clear its entry state."""
        to_cancel = []
        with self._lock:
            self.settled_tickers.add(ticker)
            cleared = []
            for client_order_id, entry in list(self.entries.items()):
                if entry.ticker == ticker:
                    if entry.stop_order_id:
                        to_cancel.append(
                            (entry.stop_order_id, entry.stop_client_order_id)
                        )
                    cleared.append(client_order_id)

            for client_order_id in cleared:
                entry = self.entries.pop(client_order_id)
                if entry.order_id:
                    self.order_id_to_client.pop(entry.order_id, None)
                if entry.stop_order_id:
                    self.order_id_to_client.pop(entry.stop_order_id, None)
                # Clean up stop_to_parent_entry_price for entries being settled
                for oid in list(self.stop_to_parent_entry_price.keys()):
                    if self.order_id_to_client.get(oid) == client_order_id:
                        del self.stop_to_parent_entry_price[oid]

        # Cancel orders outside the lock to avoid blocking during network calls
        for order_id, coid in to_cancel:
            self._cancel_order(order_id, coid)

        self.trade_log.log_event(
            "settlement",
            {
                "ticker": ticker,
                "result": result,
                "settlement_price": settlement_price,
            },
        )
        logger.info("Cleared state for settled ticker %s", ticker)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_client_id(
        self, order_id: str | None, client_order_id: str | None
    ) -> str | None:
        if client_order_id:
            return client_order_id
        if order_id:
            with self._lock:
                return self.order_id_to_client.get(order_id)
        return None

    def classify_order(self, order_id: str | None) -> str:
        """Classify an order as 'entry', 'stop', 'take_profit', or 'unknown'."""
        if not order_id:
            return "unknown"
        if order_id in self.entry_order_ids:
            return "entry"
        if order_id in self.stop_order_ids:
            return "stop"
        if order_id in self.tp_order_ids:
            return "take_profit"
        return "unknown"

    def _cancel_order(self, order_id: str | None, client_order_id: str | None) -> None:
        if not order_id:
            return
        try:
            self.rest.delete(f"/portfolio/events/orders/{order_id}")
            logger.info("Canceled order %s (client=%s)", order_id, client_order_id)
        except Exception:
            logger.exception("Failed to cancel order %s", order_id)

    def cancel_all_entries(self) -> None:
        """Cancel all resting entry orders."""
        to_cancel = []
        with self._lock:
            for entry in list(self.entries.values()):
                if entry.order_id and entry.remaining_count > Decimal("0"):
                    to_cancel.append((entry.order_id, entry.client_order_id))

        # Cancel orders outside the lock to avoid blocking during network calls
        for order_id, coid in to_cancel:
            self._cancel_order(order_id, coid)

    def cancel_all_take_profits(self) -> None:
        """Cancel all take-profit orders (used in last minute before settlement)."""
        to_cancel = []
        with self._lock:
            for entry in list(self.entries.values()):
                if entry.tp_order_id and not entry.tp_filled:
                    to_cancel.append((entry.tp_order_id, entry.tp_client_order_id))
                    self.tp_order_ids.discard(entry.tp_order_id)
                    self.order_id_to_client.pop(entry.tp_order_id, None)
                    entry.tp_order_id = None
                    entry.tp_client_order_id = None
                    entry.tp_filled = False
                    entry.tp_price = None

        for order_id, coid in to_cancel:
            self._cancel_order(order_id, coid)
            logger.info("Canceled take-profit order %s", order_id)

    def reset_window(self) -> None:
        """Clear tracked entries for a new window.

        Note: this should only be called after confirming no positions remain
        for the previous window. State is normally cleared via on_settlement().
        """
        with self._lock:
            self.entries.clear()
            self.order_id_to_client.clear()
            self.entry_order_ids.clear()
            self.stop_order_ids.clear()
            self.stop_to_parent_entry_price.clear()
