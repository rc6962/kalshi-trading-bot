"""Orderbook parsing and maker-price derivation."""

import logging
from decimal import Decimal
from typing import Any

from kalshi.rest_client import KalshiRestClient

logger = logging.getLogger(__name__)


def _best_bid(levels: list[list[str]]) -> Decimal | None:
    """Return best (highest) bid price from ascending-sorted levels."""
    if not levels:
        return None
    return Decimal(levels[-1][0])


def parse_orderbook(data: dict[str, Any]) -> dict[str, Any]:
    """Parse Kalshi bid-only orderbook into canonical prices.

    Returns:
        {
            "yes_bid": Decimal,
            "yes_ask": Decimal,
            "no_bid": Decimal,
            "no_ask": Decimal,
            "yes_spread": Decimal,
            "no_spread": Decimal,
            "raw": data,
        }
    """
    ob = data.get("orderbook_fp", {})
    yes_levels = ob.get("yes_dollars", [])
    no_levels = ob.get("no_dollars", [])

    best_yes_bid = _best_bid(yes_levels)
    best_no_bid = _best_bid(no_levels)

    if best_yes_bid is None or best_no_bid is None:
        raise ValueError("Orderbook missing yes or no bids")

    best_yes_ask = Decimal("1.00") - best_no_bid
    best_no_ask = Decimal("1.00") - best_yes_bid

    return {
        "yes_bid": best_yes_bid,
        "yes_ask": best_yes_ask,
        "no_bid": best_no_bid,
        "no_ask": best_no_ask,
        "yes_spread": best_yes_ask - best_yes_bid,
        "no_spread": best_no_ask - best_no_bid,
        "raw": data,
    }


def compute_maker_entry_prices(
    parsed: dict[str, Any],
    improvement: Decimal = Decimal("0.01"),
) -> dict[str, Any]:
    """Compute resting maker prices for YES-buy and NO-buy entries.

    - YES entry: bid side. Improve by `improvement` if spread allows, else join.
    - NO entry: sell YES (ask side). Improve by `improvement` if spread allows, else join.
      NO buy at price P == YES ask at price (1 - P).

    Returns:
        {
            "yes_bid_maker": Decimal,   # price to bid for YES entry
            "yes_ask_maker": Decimal,   # price to ask for YES entry (NO-buy)
        }
    """
    yes_bid = parsed["yes_bid"]
    yes_ask = parsed["yes_ask"]
    spread = parsed["yes_spread"]

    if spread >= 2 * improvement:
        yes_bid_maker = min(yes_bid + improvement, yes_ask - improvement)
        yes_ask_maker = max(yes_ask - improvement, yes_bid + improvement)
    else:
        # Tight spread: join the touch to guarantee maker status
        yes_bid_maker = yes_bid
        yes_ask_maker = yes_ask

    # Clamp to valid range
    yes_bid_maker = max(Decimal("0.01"), min(Decimal("0.99"), yes_bid_maker))
    yes_ask_maker = max(Decimal("0.01"), min(Decimal("0.99"), yes_ask_maker))

    return {
        "yes_bid_maker": yes_bid_maker,
        "yes_ask_maker": yes_ask_maker,
        "joined": spread < 2 * improvement,
    }


class OrderbookClient:
    """Convenience client for fetching and parsing orderbooks."""

    def __init__(self, rest: KalshiRestClient | None = None):
        self.rest = rest or KalshiRestClient()

    def get_parsed(self, ticker: str) -> dict[str, Any]:
        data = self.rest.get_orderbook(ticker)
        return parse_orderbook(data)

    def get_maker_prices(self, ticker: str, improvement: Decimal = Decimal("0.01")) -> dict[str, Any]:
        parsed = self.get_parsed(ticker)
        maker = compute_maker_entry_prices(parsed, improvement)
        return {**parsed, **maker}
