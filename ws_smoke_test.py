"""WebSocket smoke test: connect, subscribe, listen briefly."""

import asyncio
import logging
import sys

from kalshi.market_discovery import find_active_market
from kalshi.rest_client import KalshiRestClient
from kalshi.ws_client import KalshiWebSocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> int:
    rest = KalshiRestClient()
    market = find_active_market(rest, "BTC")
    if not market:
        logger.error("No BTC market found")
        return 1

    ws = KalshiWebSocket()

    async def printer(data: dict) -> None:
        logger.info("WS message: %s", data.get("type") or data.get("channel"))

    ws.register_callback("fill", printer)
    ws.register_callback("orderbook_delta", printer)
    ws.register_callback("settled", printer)

    listen_task = asyncio.create_task(ws.listen())
    # Wait for connect
    for _ in range(10):
        if ws.connected:
            break
        await asyncio.sleep(0.5)

    if not ws.connected:
        logger.error("WebSocket did not connect")
        await ws.close()
        return 1

    try:
        await ws.subscribe([market["ticker"]])
    except Exception as exc:
        logger.error("Subscribe failed: %s", exc)
        await ws.close()
        return 1

    logger.info("Listening for 10 seconds...")
    await asyncio.sleep(10)
    await ws.close()
    listen_task.cancel()
    try:
        await listen_task
    except asyncio.CancelledError:
        pass

    logger.info("WebSocket smoke test complete")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
