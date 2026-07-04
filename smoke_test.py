"""Smoke test: verify auth, balance, and market data without placing orders."""

import logging
import sys

from kalshi.market_discovery import find_active_market
from kalshi.orderbook import OrderbookClient
from kalshi.rest_client import KalshiRestClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    logger.info("Starting smoke test...")

    try:
        rest = KalshiRestClient()
        logger.info("REST client initialized")
    except Exception as exc:
        logger.error("Failed to initialize REST client: %s", exc)
        return 1

    try:
        balance = rest.get_balance()
        logger.info("Balance response: %s", balance)
    except Exception as exc:
        logger.error("Failed to fetch balance: %s", exc)
        return 1

    try:
        market = find_active_market(rest, "BTC", max_retries=30, retry_delay=2.0)
        if not market:
            logger.error("No active BTC 15-min market found")
            return 1
        logger.info("Active BTC market: %s", market["ticker"])
    except Exception as exc:
        logger.error("Failed to discover BTC market: %s", exc)
        return 1

    try:
        ob = OrderbookClient(rest)
        parsed = ob.get_parsed(market["ticker"])
        logger.info(
            "BTC orderbook: YES bid=%s ask=%s | NO bid=%s ask=%s",
            parsed["yes_bid"],
            parsed["yes_ask"],
            parsed["no_bid"],
            parsed["no_ask"],
        )
    except Exception as exc:
        logger.error("Failed to fetch orderbook: %s", exc)
        return 1

    logger.info("Smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
