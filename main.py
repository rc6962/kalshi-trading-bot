"""Kalshi 15-Min Crypto Window Bot.

Live-trading bot for Kalshi 15-minute crypto prediction markets.
Places maker-limit entries at window open, dual stop-loss ladder on fill,
and holds survivors to expiry.
"""

import argparse
import asyncio
import json
import logging
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from config.settings import get_settings
from kalshi.market_discovery import (
    ASSET_TO_SERIES,
    _market_close_time,
    discover_markets,
)
from kalshi.order_manager import OrderManager
from kalshi.orderbook import OrderbookClient
from kalshi.rest_client import KalshiRestClient
from kalshi.risk_guard import RiskGuard, estimated_max_loss_for_window
from kalshi.ws_client import KalshiWebSocket
from storage.trade_log import TradeLog


class _EstFormatter(logging.Formatter):
    """Custom formatter that shows timestamps in Eastern time."""

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return _fmt_est(dt)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log"),
    ],
)
# Replace the default formatter with our Eastern-time one
for handler in logging.getLogger().handlers:
    handler.setFormatter(
        _EstFormatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
logger = logging.getLogger(__name__)

ALL_ASSETS = list(ASSET_TO_SERIES.keys())

# EDT offset for July 2026 (UTC-4).  We use a fixed offset for display;
# the actual trading logic is always in UTC.
_EST_OFFSET = timedelta(hours=-4) if time.localtime().tm_isdst else timedelta(hours=-5)


def _fmt_est(dt: datetime) -> str:
    """Format a UTC datetime as readable Eastern time.
    Returns e.g. "July 5th 5:42am" or "December 25th 3:15pm".
    """
    est = dt + _EST_OFFSET
    hour = est.hour
    ampm = "am" if hour < 12 else "pm"
    if hour == 0:
        hour = 12
    elif hour > 12:
        hour -= 12
    day = est.day
    if 11 <= day <= 13:
        suffix = "th"
    elif day % 10 == 1:
        suffix = "st"
    elif day % 10 == 2:
        suffix = "nd"
    elif day % 10 == 3:
        suffix = "rd"
    else:
        suffix = "th"
    return f"{est.strftime('%B')} {day}{suffix} {hour}:{est.minute:02d}{ampm}"


@dataclass
class BotConfig:
    yes_assets: list[str]
    no_assets: list[str]
    contracts: int
    stop_width: Decimal
    daily_loss_cap: float
    live_mode: bool


def _multi_select(
    prompt: str, options: list[str], defaults: list[str] | None = None
) -> list[str]:
    print(f"\n{prompt}")
    for i, opt in enumerate(options, 1):
        marker = " [default]" if defaults and opt in defaults else ""
        print(f"  {i}. {opt}{marker}")
    print(
        "Enter numbers separated by commas (e.g., 1,2), or 'all', or press Enter for defaults."
    )
    raw = input("> ").strip()
    if not raw:
        return defaults or []
    if raw.lower() == "all":
        return list(options)
    selected = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            idx = int(part) - 1
            if 0 <= idx < len(options):
                selected.append(options[idx])
        except ValueError:
            logger.warning("Ignoring invalid selection: %s", part)
    return selected


def _prompt_int(prompt: str, default: int) -> int:
    raw = input(f"{prompt} [{default}]: ").strip()
    return int(raw) if raw.isdigit() else default


def _prompt_decimal(prompt: str, default: Decimal) -> Decimal:
    raw = input(f"{prompt} [{default}]: ").strip()
    return Decimal(raw) if raw else default


def _prompt_float(prompt: str, default: float) -> float:
    raw = input(f"{prompt} [{default}]: ").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def interactive_startup() -> BotConfig:
    """Run interactive command-line startup prompts."""
    print("=" * 60)
    print("Kalshi 15-Min Crypto Window Bot")
    print("=" * 60)
    print("WARNING: This bot trades real money if live mode is enabled.\n")

    yes_assets = _multi_select(
        "Select assets to BUY YES:",
        ALL_ASSETS,
        defaults=["BTC"],
    )
    no_assets = _multi_select(
        "Select assets to BUY NO (sell YES):",
        ALL_ASSETS,
        defaults=["ETH"],
    )

    overlap = set(yes_assets) & set(no_assets)
    if overlap:
        print(
            f"\nWARNING: {overlap} selected for BOTH YES and NO. This flattens exposure on the same ticker."
        )
        ok = input("Continue anyway? (yes/no): ").strip().lower()
        if ok != "yes":
            sys.exit(0)

    settings = get_settings()
    contracts = _prompt_int("Contracts per side, per asset", settings.default_contracts)
    stop_width = _prompt_decimal(
        "Stop-loss width in dollars", Decimal(str(settings.default_stop_width))
    )
    daily_loss_cap = _prompt_float("Daily loss cap (0 to disable)", 0.0)

    print("\nLive trading confirmation:")
    print("Type YES exactly to connect to Kalshi PRODUCTION and trade real money.")
    print("Anything else will exit.")
    live = input("> ").strip()
    live_mode = live == "YES"

    if not live_mode:
        print("Live mode not confirmed. Exiting.")
        sys.exit(0)

    config = BotConfig(
        yes_assets=yes_assets,
        no_assets=no_assets,
        contracts=contracts,
        stop_width=stop_width,
        daily_loss_cap=daily_loss_cap,
        live_mode=True,
    )

    print("\n" + "=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    print(f"YES assets:      {yes_assets}")
    print(f"NO assets:       {no_assets}")
    print(f"Contracts:       {contracts}")
    print(f"Stop width:      ${stop_width}")
    print(f"Daily loss cap:  ${daily_loss_cap if daily_loss_cap > 0 else 'disabled'}")
    print(f"Live mode:       {live_mode}")
    print("=" * 60)

    confirm = input("\nProceed? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    return config


class WindowBot:
    """Core bot orchestrating windows, orders, and WebSocket events."""

    def __init__(self, config: BotConfig):
        self.config = config
        self.settings = get_settings()
        self.rest = KalshiRestClient()
        self.ws = KalshiWebSocket()
        self.trade_log = TradeLog()
        self.order_manager = OrderManager(self.rest, self.trade_log)
        self.risk_guard = RiskGuard(self.rest)
        self.orderbook = OrderbookClient(self.rest)
        self.current_markets: dict[str, dict[str, Any]] = {}
        self.current_window_id: str = ""
        self.current_window_close: datetime | None = None
        self._shutdown = False
        self.reentry_candidates: set[str] = (
            set()
        )  # assets whose TP filled, waiting for 50/50
        self._asset_mid_prices: dict[str, Decimal] = {}  # latest mid-price per asset
        self._last_skip_reason: str = ""  # ticker-side:price that caused last skip
        self._skipped_close: datetime | None = (
            None  # close time we skipped, to prevent re-trigger
        )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Run the bot until shutdown."""
        self.trade_log.log_event("startup", {"config": self.config.__dict__})

        # Start WebSocket listener in background
        ws_task = asyncio.create_task(self.ws.listen())
        # Give WS a moment to connect
        await asyncio.sleep(2)

        # Register callbacks
        self.ws.register_callback("fill", self._on_fill)
        self.ws.register_callback("settled", self._on_settled)
        self.ws.register_callback("determined", self._on_determined)
        self.ws.register_callback("orderbook_delta", self._on_orderbook_delta)

        # Immediately discover markets and subscribe so price data flows.
        # This lets the bot detect 50/50 mid-window for early entry.
        all_assets = list(set(self.config.yes_assets + self.config.no_assets))
        try:
            markets = await asyncio.to_thread(discover_markets, self.rest, all_assets)
            if markets:
                tickers = [m["ticker"] for m in markets.values()]
                await self.ws.subscribe(tickers)
                logger.info(
                    "Subscribed to %d tickers on startup: %s", len(tickers), tickers
                )
        except Exception:
            logger.debug("No active markets at startup — will retry in main loop")

        try:
            while not self._shutdown:
                if self.risk_guard.kill_switch_active():
                    logger.warning("Kill switch active. Halting new entries.")
                    await asyncio.sleep(5)
                    continue

                if self.risk_guard.check_daily_loss(
                    self._daily_realized_pnl(), self.config.daily_loss_cap
                ):
                    logger.warning("Daily loss cap reached. Halting new entries.")
                    await asyncio.sleep(60)
                    continue

                if not self.ws.connected:
                    logger.warning("WebSocket not connected. Waiting...")
                    await asyncio.sleep(5)
                    continue

                next_open = self._next_window_open()
                wait_seconds = (next_open - datetime.now(timezone.utc)).total_seconds()
                pre_open_buffer = 10
                sleep_seconds = max(0, wait_seconds - pre_open_buffer)
                if sleep_seconds > 10:
                    entered_early = False
                    while sleep_seconds > 10 and not self._shutdown:
                        # Show prices + countdown every 10s
                        price_parts = []
                        for asset in sorted(
                            set(self.config.yes_assets + self.config.no_assets)
                        ):
                            mid = self._asset_mid_prices.get(asset)
                            price_parts.append(
                                f"{asset}=${mid:.4f}" if mid else f"{asset}=?"
                            )
                        price_status = " | ".join(price_parts)
                        logger.info(
                            "Next window at %s ET — T-minus %.0fs — %s",
                            _fmt_est(next_open),
                            sleep_seconds,
                            price_status,
                        )

                        # Probe for markets every 10s if we haven't already
                        # found them (current_markets is empty = not in a window)
                        if not self.current_markets:
                            try:
                                markets = await asyncio.to_thread(
                                    discover_markets,
                                    self.rest,
                                    list(
                                        set(
                                            self.config.yes_assets
                                            + self.config.no_assets
                                        )
                                    ),
                                )
                                if markets:
                                    earliest_close = min(
                                        _market_close_time(m)
                                        for m in markets.values()
                                        if _market_close_time(m)
                                    )
                                    if earliest_close:
                                        left = (
                                            earliest_close - datetime.now(timezone.utc)
                                        ).total_seconds()
                                        if left > 180:
                                            logger.info(
                                                "Markets found — entering window"
                                            )
                                            entered_early = True
                                            break
                            except Exception:
                                pass

                        await asyncio.sleep(min(10, sleep_seconds - 10))
                        sleep_seconds = max(
                            0,
                            (next_open - datetime.now(timezone.utc)).total_seconds()
                            - 10,
                        )

                    if entered_early:
                        await self._execute_window()
                        continue
                elif sleep_seconds > 0:
                    await asyncio.sleep(sleep_seconds)

                await self._execute_window()
        except asyncio.CancelledError:
            logger.info("Bot loop cancelled")
        finally:
            await self._shutdown_bot(ws_task)

    async def _execute_window(self) -> None:
        """Run one trading window."""
        now = datetime.now(timezone.utc)
        self.current_window_id = _fmt_est(now)
        logger.info("=== Starting window %s ===", self.current_window_id)

        all_assets = list(set(self.config.yes_assets + self.config.no_assets))
        self.reentry_candidates.clear()

        # Poll until Kalshi actually lists the active markets, up to 60 seconds
        self.current_markets = await self._wait_for_active_markets(
            all_assets, timeout_seconds=60
        )
        if not self.current_markets:
            logger.warning(
                "No active markets found for window %s after polling",
                self.current_window_id,
            )
            self._skipped_close = None
            return

        # Record the actual window close time from the market metadata
        close_times = [
            _market_close_time(m)
            for m in self.current_markets.values()
            if _market_close_time(m)
        ]
        if close_times:
            self.current_window_close = min(close_times)
            logger.info(
                "Window close time set to %s", self.current_window_close.isoformat()
            )

        # If we already skipped this exact window close time, don't re-check
        if self._skipped_close and self.current_window_close == self._skipped_close:
            logger.info("Already skipped this window — waiting for next")
            return

        # Tiny randomized wait so the book has a moment to form
        await asyncio.sleep(random.uniform(0.5, 1.5))

        # Fetch orderbooks and build entry plan
        planned_entries = []
        for asset in self.config.yes_assets:
            market = self.current_markets.get(asset.upper())
            if not market:
                continue
            try:
                book = await asyncio.to_thread(
                    self.orderbook.get_maker_prices,
                    market["ticker"],
                    Decimal(str(self.settings.entry_improvement)),
                )
                planned_entries.append(
                    {
                        "asset": asset.upper(),
                        "ticker": market["ticker"],
                        "side": "bid",
                        "price": book["yes_bid_maker"],
                        "count": Decimal(self.config.contracts),
                    }
                )
            except Exception:
                logger.exception("Failed to get orderbook for %s", asset)

        for asset in self.config.no_assets:
            market = self.current_markets.get(asset.upper())
            if not market:
                continue
            try:
                book = await asyncio.to_thread(
                    self.orderbook.get_maker_prices,
                    market["ticker"],
                    Decimal(str(self.settings.entry_improvement)),
                )
                planned_entries.append(
                    {
                        "asset": asset.upper(),
                        "ticker": market["ticker"],
                        "side": "ask",
                        "price": book["yes_ask_maker"],
                        "count": Decimal(self.config.contracts),
                    }
                )
            except Exception:
                logger.exception("Failed to get orderbook for %s", asset)

        if not planned_entries:
            logger.warning("No planned entries for window %s", self.current_window_id)
            return

        # Subscribe to tickers immediately so WS data starts flowing,
        # even if we skip this window due to prices.
        tickers = [e["ticker"] for e in planned_entries]
        try:
            await self.ws.subscribe(tickers)
        except Exception:
            logger.exception("Failed to subscribe to tickers")

        # Re-entry check for price change — if we skipped this window
        # before and prices have moved (cached via WS), try again.
        if self.current_markets and self._last_skip_reason:
            prices_now = ""
            for asset in sorted(set(self.config.yes_assets + self.config.no_assets)):
                m = self._asset_mid_prices.get(asset)
                prices_now += f"{asset}={m or 0} "
            if prices_now == self._last_skip_reason:
                logger.info("Prices unchanged since last skip — skipping window")
                self._skipped_close = self.current_window_close
                return
            else:
                logger.info("Prices changed — re-checking entry conditions")
                self._last_skip_reason = ""

        # Sanity check: skip if any entry price is too far from 50/50
        for plan in planned_entries:
            p = Decimal(str(plan["price"]))
            if p < Decimal("0.40") or p > Decimal("0.60"):
                logger.warning(
                    "%s entry price %.4f too far from 50/50 — skipping window",
                    plan["asset"],
                    p,
                )
                # Record the price snapshot so the probe won't retry until prices change
                prices = ""
                for asset in sorted(
                    set(self.config.yes_assets + self.config.no_assets)
                ):
                    m = self._asset_mid_prices.get(asset)
                    prices += f"{asset}={m or 0} "
                self._last_skip_reason = prices
                self._skipped_close = self.current_window_close
                return

        # Risk checks
        max_loss = estimated_max_loss_for_window(planned_entries)
        if not self.risk_guard.check_balance(max_loss):
            logger.warning("Insufficient balance for estimated max loss %.2f", max_loss)
            return

        if not self.risk_guard.check_exchange_status():
            logger.warning("Exchange not active; skipping window")
            return

        # Re-subscribe WS to current tickers
        tickers = [e["ticker"] for e in planned_entries]
        try:
            await self.ws.subscribe(tickers)
        except Exception:
            logger.exception("Failed to subscribe to tickers")

        # Place entries — they either fill (via WS) or expire at market close.
        # The bot stays live streaming Kalshi data the entire time.
        self._skipped_close = None  # reset skip guard — we're entering
        for plan in planned_entries:
            try:
                self.order_manager.place_entry(
                    ticker=plan["ticker"],
                    asset=plan["asset"],
                    side=plan["side"],
                    price=plan["price"],
                    count=plan["count"],
                    stop_width=self.config.stop_width,
                )
            except Exception:
                logger.exception("Failed to place entry for %s", plan["asset"])

        # Live status loop: display prices, positions, and countdown until T-60s
        # (when unfilled take-profits get canceled).
        if self.current_window_close:
            close_time = self.current_window_close
            while True:
                now_dt = datetime.now(timezone.utc)
                remaining = (close_time - now_dt).total_seconds()

                if remaining <= 60:
                    break

                # Build status line
                parts = []
                for asset in sorted(
                    set(self.config.yes_assets + self.config.no_assets)
                ):
                    mid = self._asset_mid_prices.get(asset)
                    price_str = f"${mid:.4f}" if mid else "?"

                    # Check if this asset has an active filled entry
                    side_label = ""
                    for entry in self.order_manager.entries.values():
                        if entry.asset == asset and entry.filled_count > 0:
                            side_label = "▲" if entry.side == "bid" else "▼"
                            break

                    # Check re-entry status
                    re_flag = "⏳R" if asset in self.reentry_candidates else ""

                    parts.append(f"{asset}={price_str}{side_label}{re_flag}")

                status = " | ".join(parts)
                logger.info(
                    "[%s] %s — T-%.0fs until TP cancel, window closes in %.0fs",
                    self.current_window_id,
                    status,
                    max(0, remaining - 60),
                    remaining,
                )

                await asyncio.sleep(10)

        self.order_manager.cancel_all_take_profits()
        logger.info("Canceled take-profit orders — survivors ride to $1.00 settlement")

        # The WS orderbook_delta callback continues monitoring stop/TP proximity
        # for ALL assets and only escalates to IOC if BOTH limit stops are bypassed.
        logger.info(
            "=== Window %s — monitoring stops, waiting for settlement ===",
            self.current_window_id,
        )

    # ------------------------------------------------------------------
    # WebSocket callbacks
    # ------------------------------------------------------------------

    async def _on_fill(self, data: dict[str, Any]) -> None:
        """Handle fill WebSocket messages."""
        msg = data.get("msg", data)
        order_id = msg.get("order_id")
        client_order_id = msg.get("client_order_id")
        fill_price = (
            msg.get("yes_price_dollars")
            or msg.get("price_dollars")
            or msg.get("fill_price_dollars")
        )
        fill_count = msg.get("count_fp") or msg.get("fill_count")

        ticker = msg.get("market_ticker") or msg.get("ticker")

        if not fill_price or not fill_count:
            logger.debug("Fill message missing price/count: %s", data)
            return

        role = self.order_manager.classify_order(order_id)
        if role == "entry":
            await asyncio.to_thread(
                self.order_manager.on_entry_fill,
                order_id,
                client_order_id,
                str(fill_price),
                str(fill_count),
                "maker",
            )
        elif role == "stop":
            await asyncio.to_thread(
                self.order_manager.on_stop_fill,
                order_id,
                client_order_id,
                str(fill_price),
                str(fill_count),
                "taker",
            )
            # Stop filled — position closed at a loss. Mark as re-entry eligible
            # so if the whole session closes and returns to 50/50, we can retry.
            if ticker:
                for asset, market in self.current_markets.items():
                    if market.get("ticker") == ticker:
                        self.reentry_candidates.add(asset)
                        logger.info(
                            "Stop filled for %s — added to re-entry candidates",
                            asset,
                        )
                        break
        elif role == "take_profit":
            await asyncio.to_thread(
                self.order_manager.on_tp_fill,
                order_id,
                client_order_id,
                str(fill_price),
                str(fill_count),
                "taker",
            )
            # TP filled — position closed with profit. Mark as re-entry eligible.
            if ticker:
                for asset, market in self.current_markets.items():
                    if market.get("ticker") == ticker:
                        self.reentry_candidates.add(asset)
                        logger.info(
                            "TP filled for %s — added to re-entry candidates",
                            asset,
                        )
                        break
        else:
            logger.warning(
                "Unclassified fill: order_id=%s client_order_id=%s",
                order_id,
                client_order_id,
            )

    async def _on_settled(self, data: dict[str, Any]) -> None:
        """Handle market settlement events."""
        msg = data.get("msg", data)
        ticker = msg.get("market_ticker") or msg.get("ticker")
        result = msg.get("result")
        settlement_price = msg.get("settlement_value") or msg.get(
            "settlement_price_dollars"
        )
        logger.info("Settlement: %s -> %s @ %s", ticker, result, settlement_price)
        await asyncio.to_thread(
            self.order_manager.on_settlement,
            ticker,
            result,
            settlement_price,
        )

        # Clear this ticker from current_markets so the probe can
        # discover the next window's market
        for asset, market in list(self.current_markets.items()):
            if market.get("ticker") == ticker:
                del self.current_markets[asset]
                break

    async def _on_determined(self, data: dict[str, Any]) -> None:
        """Handle market determination events."""
        msg = data.get("msg", data)
        ticker = msg.get("market_ticker") or msg.get("ticker")
        result = msg.get("result")
        logger.info("Determined: %s -> %s", ticker, result)

    async def _on_orderbook_delta(self, data: dict[str, Any]) -> None:
        """Handle orderbook updates. Monitor stop/TP proximity for all assets.

        For each active entry on this ticker:
          - Stop escalation: only fires IoC if BOTH limit stops are bypassed
          - TP proximity: logs when price nears the TP level
        """
        msg = data.get("msg", data)
        ticker = msg.get("market_ticker") or msg.get("ticker")

        # Extract current market prices from orderbook
        yes_bids = msg.get("yes_bids", [])
        yes_asks = msg.get("yes_asks", [])

        if not yes_bids and not yes_asks:
            return

        # Get best prices
        best_bid = float(yes_bids[0][0]) if yes_bids else 0.0
        best_ask = float(yes_asks[0][0]) if yes_asks else 0.0
        market_price = (best_bid + best_ask) / 2

        # Cache latest mid-price for re-entry checks
        for asset, market in self.current_markets.items():
            if market.get("ticker") == ticker:
                self._asset_mid_prices[asset] = Decimal(str(market_price))
                break

        # Route to OrderManager: check stop levels and TP proximity
        await asyncio.to_thread(
            self.order_manager.check_stop_escalation,
            ticker,
            market_price,
        )

        # TP proximity check — log when price is within 2¢ of take-profit level
        await asyncio.to_thread(
            self.order_manager.check_tp_proximity,
            ticker,
            market_price,
        )

        # Re-entry check — if any asset had a TP fill and price returned to 50/50
        await self._check_reentry(ticker, market_price)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _wait_for_active_markets(
        self,
        assets: list[str],
        timeout_seconds: float = 60,
        poll_interval: float = 2.0,
    ) -> dict[str, dict[str, Any]]:
        """Poll Kalshi until active markets are listed, then return them."""
        deadline = datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)
        while datetime.now(timezone.utc) < deadline:
            try:
                markets = await asyncio.to_thread(discover_markets, self.rest, assets)
                if markets:
                    return markets
            except Exception:
                logger.exception("Market discovery poll failed")
            await asyncio.sleep(poll_interval)
        return {}

    def _next_window_open(self) -> datetime:
        """Return the next 15-minute boundary (:00, :15, :30, :45).

        If exactly on a boundary, add a small grace period so that discovery
        happens after the window has actually opened rather than the exact
        moment (which can race with exchange listing).
        """
        now = datetime.now(timezone.utc)
        aligned = now.replace(second=0, microsecond=0)
        minutes_to_add = 15 - (now.minute % 15)
        if minutes_to_add == 15:
            minutes_to_add = 0
        return aligned + timedelta(minutes=minutes_to_add, seconds=2)

    async def _check_reentry(self, ticker: str, market_price: float) -> None:
        """Check whether ALL session assets have TP'd and returned to 50/50.
        If so, re-enter all of them together with their partner assets.

        Only re-enters if there are >3 minutes until expiry to give the
        new positions time to work.
        """
        session_assets = list(set(self.config.yes_assets + self.config.no_assets))
        if not session_assets:
            return

        # Must be >3 minutes remaining to give new positions time to work
        if self.current_window_close:
            remaining = (
                self.current_window_close - datetime.now(timezone.utc)
            ).total_seconds()
            if remaining < 180:
                self.reentry_candidates.clear()
                return

        # Check if ALL session assets have TP'd and all are near 50/50
        for asset in session_assets:
            if asset not in self.reentry_candidates:
                return  # not all TP'd yet — keep waiting

        all_near_50 = True
        for asset in session_assets:
            mid = self._asset_mid_prices.get(asset)
            if mid is None or mid < Decimal("0.47") or mid > Decimal("0.53"):
                all_near_50 = False
                break

        if not all_near_50:
            return

        # ALL session assets are TP'd and all are near 50/50 — re-enter everything
        logger.info(
            "=== Session re-entry triggered — all assets near 50/50: %s ===",
            session_assets,
        )
        self.reentry_candidates.clear()

        for asset in session_assets:
            market = self.current_markets.get(asset)
            if not market:
                continue

            try:
                book = await asyncio.to_thread(
                    self.orderbook.get_maker_prices,
                    market["ticker"],
                    Decimal(str(self.settings.entry_improvement)),
                )
            except Exception:
                logger.exception("Failed to get orderbook for re-entry of %s", asset)
                continue

            if asset in self.config.yes_assets:
                self.order_manager.place_entry(
                    ticker=market["ticker"],
                    asset=asset,
                    side="bid",
                    price=book["yes_bid_maker"],
                    count=Decimal(self.config.contracts),
                )
            if asset in self.config.no_assets:
                self.order_manager.place_entry(
                    ticker=market["ticker"],
                    asset=asset,
                    side="ask",
                    price=book["yes_ask_maker"],
                    count=Decimal(self.config.contracts),
                )

            logger.info(
                "Re-entry orders placed for %s — bid=%s ask=%s",
                asset,
                book.get("yes_bid_maker"),
                book.get("yes_ask_maker"),
            )

    def _daily_realized_pnl(self) -> float:
        """Calculate accurate realized PnL from completed trades today.

        Uses stop_fill and settlement events to compute exact profit/loss.
        Aggregates partial fills per entry (by client_order_id) to avoid double-counting.
        """
        from collections import defaultdict

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        pnl = 0.0

        # Read all stop_fill and settlement events from today
        stop_fills = []
        settlements = []
        entry_fills = []

        for event in self.trade_log.read_events("stop_fill"):
            if not event.get("ts", "").startswith(today):
                continue
            stop_fills.append(event)

        for event in self.trade_log.read_events("settlement"):
            if not event.get("ts", "").startswith(today):
                continue
            settlements.append(event)

        for event in self.trade_log.read_events("fill"):
            if not event.get("ts", "").startswith(today):
                continue
            if event.get("fill_side") == "maker":
                entry_fills.append(event)

        # Build set of entry client_order_ids that were closed by stops
        stopped_entry_ids: set[str] = set()
        for stop_event in stop_fills:
            parent_id = stop_event.get("parent_entry_client_order_id")
            if parent_id:
                stopped_entry_ids.add(parent_id)

        # Aggregate partial fills by entry (client_order_id) to get total filled
        # This prevents double-counting when an entry has multiple partial fills
        entries_by_client_id: dict[str, dict[str, Any]] = {}
        for fill_event in entry_fills:
            client_id = fill_event.get("client_order_id")
            if not client_id:
                continue

            if client_id not in entries_by_client_id:
                entries_by_client_id[client_id] = {
                    "ticker": fill_event["ticker"],
                    "side": fill_event.get("side", "bid"),
                    "entry_price": float(fill_event.get("entry_price", "0.0")),
                    "total_filled": Decimal("0"),
                }
            entries_by_client_id[client_id]["total_filled"] += Decimal(
                fill_event.get("fill_count", "0")
            )

        # Pre-bucket entries by ticker for O(1) lookup during settlement
        entries_by_ticker: dict[str, list[str]] = defaultdict(list)
        for client_id, entry in entries_by_client_id.items():
            entries_by_ticker[entry["ticker"]].append(client_id)

        # Process stop fills
        for stop_event in stop_fills:
            stop_price = float(stop_event["fill_price"])
            fill_count = float(stop_event["fill_count"])
            entry_price = float(stop_event.get("entry_price", "0.0"))

            if entry_price > stop_price:
                trade_pnl = (stop_price - entry_price) * fill_count
            else:
                trade_pnl = (entry_price - stop_price) * fill_count
            pnl += trade_pnl

        # Process settlements: find entries not closed by stop
        for settlement_event in settlements:
            ticker = settlement_event["ticker"]
            result = settlement_event["result"]
            settlement_price = settlement_event.get("settlement_price")
            if settlement_price is None:
                settlement_price = "0.99" if result == "yes" else "0.00"
            settlement_price = float(settlement_price)

            # Find all entry client_ids for this ticker
            client_ids = entries_by_ticker.get(ticker, [])
            if not client_ids:
                continue

            for client_id in client_ids:
                # Skip entries closed by stop-loss
                if client_id in stopped_entry_ids:
                    continue

                entry = entries_by_client_id[client_id]
                entry_price = entry["entry_price"]
                fill_count = float(entry["total_filled"])
                side = entry["side"]

                if side == "bid":
                    trade_pnl = (settlement_price - entry_price) * fill_count
                else:
                    trade_pnl = (entry_price - settlement_price) * fill_count
                pnl += trade_pnl

        return pnl

    async def _shutdown_bot(self, ws_task: asyncio.Task) -> None:
        """Graceful shutdown."""
        logger.info("Shutting down bot...")
        self._shutdown = True
        self.order_manager.cancel_all_entries()
        await self.ws.close()
        ws_task.cancel()
        try:
            await ws_task
        except asyncio.CancelledError:
            pass
        logger.info("Shutdown complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Kalshi 15-Min Crypto Window Bot")
    parser.add_argument("--yes", help="Comma-separated YES assets (overrides prompt)")
    parser.add_argument("--no", help="Comma-separated NO assets (overrides prompt)")
    parser.add_argument("--contracts", type=int, help="Contracts per side")
    parser.add_argument("--stop-width", type=float, help="Stop width in dollars")
    parser.add_argument(
        "--daily-loss-cap", type=float, default=0.0, help="Daily loss cap"
    )
    parser.add_argument(
        "--live", action="store_true", help="Skip live confirmation prompt"
    )
    parser.add_argument(
        "--last", action="store_true", help="Reuse last session's config"
    )
    args = parser.parse_args()

    # Load saved config if --last is passed
    last_config_path = Path(__file__).parent / "config" / "last_config.json"

    if args.last:
        if not last_config_path.exists():
            print("No saved config found. Run without --last first.")
            sys.exit(1)
        try:
            with open(last_config_path) as f:
                saved = json.load(f)
            config = BotConfig(
                yes_assets=saved["yes_assets"],
                no_assets=saved["no_assets"],
                contracts=saved["contracts"],
                stop_width=Decimal(str(saved["stop_width"])),
                daily_loss_cap=saved.get("daily_loss_cap", 0.0),
                live_mode=True,
            )
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"Failed to load saved config: {exc}")
            sys.exit(1)

    elif args.yes is not None:
        yes_assets = [a.strip().upper() for a in args.yes.split(",") if a.strip()]
        no_assets = [a.strip().upper() for a in (args.no or "").split(",") if a.strip()]
        contracts = args.contracts or get_settings().default_contracts
        stop_width = (
            Decimal(str(args.stop_width))
            if args.stop_width
            else Decimal(str(get_settings().default_stop_width))
        )
        if not args.live:
            print("--live flag required when using CLI args")
            sys.exit(1)
        config = BotConfig(
            yes_assets=yes_assets,
            no_assets=no_assets,
            contracts=contracts,
            stop_width=stop_width,
            daily_loss_cap=args.daily_loss_cap,
            live_mode=True,
        )
    else:
        config = interactive_startup()
        # Save config for --last flag
        try:
            with open(last_config_path, "w") as f:
                json.dump(
                    {
                        "yes_assets": config.yes_assets,
                        "no_assets": config.no_assets,
                        "contracts": config.contracts,
                        "stop_width": str(config.stop_width),
                        "daily_loss_cap": config.daily_loss_cap,
                    },
                    f,
                )
        except Exception as exc:
            logger.warning("Failed to save last config: %s", exc)

    bot = WindowBot(config)

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    main()
