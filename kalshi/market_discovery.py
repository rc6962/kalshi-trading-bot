"""Discover active 15-minute Kalshi crypto markets."""

import logging
import time
from datetime import datetime, timezone
from typing import Any

from kalshi.rest_client import KalshiRestClient

logger = logging.getLogger(__name__)

# All supported 15-min crypto series tickers
ASSET_TO_SERIES = {
    "BTC": "KXBTC15M",
    "ETH": "KXETH15M",
    "SOL": "KXSOL15M",
    "DOGE": "KXDOGE15M",
    "XRP": "KXXRP15M",
    "BNB": "KXBNB15M",
    "HYPE": "KXHYPE15M",
}


def _parse_ts_ms(ts_ms: int | None) -> datetime | None:
    if ts_ms is None:
        return None
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)


def _parse_ts_str(ts: str | None) -> datetime | None:
    if not ts:
        return None
    # Kalshi returns ISO 8601 strings; handle Z suffix
    ts = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _market_close_time(market: dict[str, Any]) -> datetime | None:
    """Extract close_time from market object, trying multiple field names."""
    for key in ("close_time", "expiration_time", "latest_expiration_time", "expected_expiration_time"):
        value = market.get(key)
        if value is None:
            continue
        if isinstance(value, int):
            return _parse_ts_ms(value)
        if isinstance(value, str):
            return _parse_ts_str(value)
    return None


def find_active_market(
    rest: KalshiRestClient,
    asset: str,
    min_seconds_remaining: int = 30,
    max_retries: int = 5,
    retry_delay: float = 1.0,
) -> dict[str, Any] | None:
    """Find the currently active 15-min market for an asset.

    Retries a few times to handle the brief gap between settlement and new listing.
    """
    series = ASSET_TO_SERIES.get(asset.upper())
    if not series:
        raise ValueError(f"Unsupported asset: {asset}")

    params = {
        "series_ticker": series,
        "status": "open",
        "limit": 20,
    }

    for attempt in range(max_retries):
        try:
            data = rest.get_markets(params)
        except Exception:
            logger.exception("Market discovery failed for %s (attempt %d)", asset, attempt + 1)
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            return None

        markets = data.get("markets", [])
        now = datetime.now(timezone.utc)
        candidates = []
        for market in markets:
            close_time = _market_close_time(market)
            if not close_time:
                continue
            if close_time.tzinfo is None:
                close_time = close_time.replace(tzinfo=timezone.utc)
            seconds_remaining = (close_time - now).total_seconds()
            if seconds_remaining >= min_seconds_remaining:
                candidates.append((seconds_remaining, market))

        if candidates:
            candidates.sort(key=lambda x: x[0])
            market = candidates[0][1]
            logger.info("Discovered market for %s: %s (closes in %.0fs)", asset, market["ticker"], candidates[0][0])
            return market

        if attempt < max_retries - 1:
            logger.info("No active market for %s yet; retrying in %.1fs...", asset, retry_delay * (attempt + 1))
            time.sleep(retry_delay * (attempt + 1))

    logger.warning("No active market found for %s after %d retries", asset, max_retries)
    return None


def discover_markets(
    rest: KalshiRestClient,
    assets: list[str],
    min_seconds_remaining: int = 30,
) -> dict[str, dict[str, Any]]:
    """Discover active markets for a list of assets.

    Returns mapping: {asset_upper: market_dict}.
    """
    result: dict[str, dict[str, Any]] = {}
    for asset in assets:
        market = find_active_market(rest, asset, min_seconds_remaining=min_seconds_remaining)
        if market:
            result[asset.upper()] = market
    return result
