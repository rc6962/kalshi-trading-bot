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


class OrderManager:
    """Manages entries, fills, and IoC aggressive stop-losses."""

    def __init__(self, rest: KalshiRestClient, trade_log: TradeLog | None = None):
        self.rest = rest
        self.trade_log = trade_log or TradeLog()
        self.entries: dict[str, EntryState] = {}  # client_order_id -> EntryState
        self.order_id_to_client: dict[str, str] = {}  # server order_id -> client_order_id
        self.settled_tickers: set[str] = set()
        self.entry_order_ids: set[str] = set()  # track all entry order_ids
        self.stop_order_ids: set[str] = set()   # track all stop order_ids
        self.stop_to_parent_entry_price: dict[str, Decimal] = {}  # stop_order_id -> entry_price
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
        stop_width: Decimal,
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
            logger.warning("Fill for unknown entry order: order_id=%s client=%s", order_id, client_order_id)
            return

        with self._lock:
            entry = self.entries[client_order_id]
            entry.filled_count += Decimal(fill_count)
            entry.remaining_count = max(Decimal("0"), entry.requested_count - entry.filled_count)

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
            self._place_ioc_stop(entry)

    def on_stop_fill(
        self,
        order_id: str | None,
        client_order_id: str | None,
        fill_price: str,
        fill_count: str,
        fill_side: str = "taker",
    ) -> None:
        """Handle a stop fill event."""
        # Try to resolve associated entry for richer logging
        asset = "unknown"
        ticker = "unknown"
        side = "unknown"
        parent_entry_client_order_id = None
        
        with self._lock:
            # The stop's client_order_id maps back to the entry via stop_client_order_id
            for entry in self.entries.values():
                if entry.stop_client_order_id == client_order_id:
                    asset = entry.asset
                    ticker = entry.ticker
                    side = entry.side
                    parent_entry_client_order_id = entry.client_order_id
                    break

        # Look up the parent entry price
        entry_price = self.stop_to_parent_entry_price.get(order_id)
        if entry_price is None:
            logger.warning("Stop fill received but no parent entry price found for order_id=%s", order_id)
            entry_price_str = "0.0000"
        else:
            entry_price_str = str(entry_price)

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
        logger.info("Stop filled: %s %s %s contracts @ %s (side=%s)", asset, ticker, fill_count, fill_price, fill_side)

    # ------------------------------------------------------------------
    # Stop placement
    # ------------------------------------------------------------------

    def _stop_side(self, entry: EntryState) -> str:
        """Return the side needed to flatten the entry."""
        return "ask" if entry.side == "bid" else "bid"

    def _stop_price(self, entry: EntryState) -> Decimal:
        """Compute aggressive IoC stop price.

        For a long YES position, we need to sell YES below current market.
        For a long NO position, we need to buy YES back above current market.
        """
        buffer = Decimal(str(self.settings.ioc_fallback_buffer))
        if entry.side == "bid":
            # Long YES: sell to flatten. Price = entry - stop_width - buffer.
            return max(Decimal("0.01"), entry.entry_price - entry.stop_width - buffer)
        else:
            # Long NO: buy YES back. Price = entry + stop_width + buffer.
            return min(Decimal("0.99"), entry.entry_price + entry.stop_width + buffer)

    def _place_ioc_stop(self, entry: EntryState) -> None:
        """Place (or replace) a single IoC reduce-only stop for current filled_count."""
        if entry.filled_count <= Decimal("0"):
            return

        # Cancel any existing stop before placing a new one
        if entry.stop_order_id:
            self._cancel_order(entry.stop_order_id, entry.stop_client_order_id)
            # Clean up old mappings
            with self._lock:
                self.order_id_to_client.pop(entry.stop_order_id, None)
                self.stop_order_ids.discard(entry.stop_order_id)

        side = self._stop_side(entry)
        price = self._stop_price(entry)
        count = entry.filled_count
        client_order_id = str(uuid.uuid4())

        payload = {
            "ticker": entry.ticker,
            "side": side,
            "count": _fmt_count(count),
            "price": _fmt_decimal(price),
            "time_in_force": "immediate_or_cancel",
            "self_trade_prevention_type": "taker_at_cross",
            "client_order_id": client_order_id,
            "reduce_only": True,
        }

        try:
            response = self.rest.post("/portfolio/events/orders", json_data=payload)
            with self._lock:
                entry.stop_order_id = response.get("order_id")
                entry.stop_client_order_id = client_order_id
            status = response.get("status", "")
            
            if not entry.stop_order_id or status in ("canceled", "rejected"):
                logger.critical(
                    "IoC stop FAILED for %s %s — position unprotected! "
                    "Manual intervention required. Entry price: %s, Stop price attempted: %s",
                    entry.asset,
                    entry.ticker,
                    entry.entry_price,
                    price
                )
                # Cancel the entry order to prevent further exposure
                self._emergency_cancel_entry(entry)
                with self._lock:
                    entry.stop_order_id = None  # Prevent retry attempts
                return

            if entry.stop_order_id:
                with self._lock:
                    self.order_id_to_client[entry.stop_order_id] = client_order_id
                    self.stop_order_ids.add(entry.stop_order_id)

            filled = Decimal(str(response.get("fill_count", "0")))
            remaining = count - filled

            self.trade_log.log_event(
                "stop_placed",
                {
                    "asset": entry.asset,
                    "ticker": entry.ticker,
                    "side": side,
                    "price": str(price),
                    "count": str(count),
                    "client_order_id": client_order_id,
                    "order_id": entry.stop_order_id,
                    "type": "ioc_aggressive",
                    "entry_price": str(entry.entry_price),
                    "filled_count": str(filled),
                    "remaining_count": str(remaining),
                },
            )
            logger.info(
                "Placed IoC stop %s %s @ %s (%s contracts, filled %s, remaining %s)",
                entry.asset,
                entry.ticker,
                price,
                count,
                filled,
                remaining,
            )

            # Track parent entry price for stop
            if entry.stop_order_id:
                with self._lock:
                    self.stop_to_parent_entry_price[entry.stop_order_id] = entry.entry_price

            if remaining > Decimal("0"):
                logger.warning(
                    "IOC stop left %s contracts unfilled for %s — escalating",
                    remaining,
                    entry.ticker
                )
                # Escalate: make price more aggressive
                # For selling (side="bid"): lower price by 0.05
                # For buying (side="ask"): raise price by 0.05
                escalated_price = self._stop_price(entry) - (Decimal("0.05") if side == "bid" else -Decimal("0.05"))
                escalated_payload = {
                    "ticker": entry.ticker,
                    "side": side,
                    "count": _fmt_count(remaining),
                    "price": _fmt_decimal(escalated_price),
                    "time_in_force": "immediate_or_cancel",
                    "self_trade_prevention_type": "taker_at_cross",
                    "client_order_id": str(uuid.uuid4()),
                    "reduce_only": True,
                }
                try:
                    retry_response = self.rest.post("/portfolio/events/orders", json_data=escalated_payload)
                    retry_filled = Decimal(str(retry_response.get("fill_count", "0")))
                    retry_remaining = remaining - retry_filled
                    if retry_remaining > Decimal("0"):
                        logger.critical(
                            "Escalated IOC stop still left %s contracts unfilled for %s — potential exposure",
                            retry_remaining,
                            entry.ticker
                        )
                        # Trigger risk guard emergency flag (to be implemented in risk_guard.py)
                        # This requires a new method in RiskGuard
                        self.trade_log.log_event(
                            "emergency_exposure",
                            {
                                "asset": entry.asset,
                                "ticker": entry.ticker,
                                "unfilled_count": str(retry_remaining),
                                "original_stop_price": str(price),
                                "escalated_stop_price": str(escalated_price),
                            }
                        )
                except Exception:
                    logger.exception("Failed to place escalated IOC stop for %s", entry.asset)

        except Exception:
            logger.exception("Failed to place IoC stop for %s", entry.asset)

    def _emergency_cancel_entry(self, entry: EntryState) -> None:
        """Cancel the entry order if IoC stop fails, to limit further fill exposure."""
        if entry.order_id and entry.remaining_count > Decimal("0"):
            logger.warning("Emergency canceling entry %s to prevent further fills", entry.asset)
            self._cancel_order(entry.order_id, entry.client_order_id)

    # ------------------------------------------------------------------
    # Settlement handling
    # ------------------------------------------------------------------

    def on_settlement(self, ticker: str, result: str, settlement_price: str | None) -> None:
        """Mark a ticker as settled and clear its entry state."""
        to_cancel = []
        with self._lock:
            self.settled_tickers.add(ticker)
            cleared = []
            for client_order_id, entry in list(self.entries.items()):
                if entry.ticker == ticker:
                    if entry.stop_order_id:
                        to_cancel.append((entry.stop_order_id, entry.stop_client_order_id))
                    cleared.append(client_order_id)

            for client_order_id in cleared:
                entry = self.entries.pop(client_order_id)
                if entry.order_id:
                    self.order_id_to_client.pop(entry.order_id, None)
                if entry.stop_order_id:
                    self.order_id_to_client.pop(entry.stop_order_id, None)

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

    def _resolve_client_id(self, order_id: str | None, client_order_id: str | None) -> str | None:
        if client_order_id:
            return client_order_id
        if order_id:
            with self._lock:
                return self.order_id_to_client.get(order_id)
        return None

    def classify_order(self, order_id: str | None) -> str:
        """Classify an order as 'entry', 'stop', or 'unknown'."""
        if not order_id:
            return "unknown"
        if order_id in self.entry_order_ids:
            return "entry"
        if order_id in self.stop_order_ids:
            return "stop"
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
