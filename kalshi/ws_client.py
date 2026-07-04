"""Async Kalshi WebSocket client with reconnect and message routing."""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine

import websockets
from websockets.exceptions import ConnectionClosed

from config.settings import get_settings
from kalshi.auth import load_private_key, sign_request

logger = logging.getLogger(__name__)

# Channels we subscribe to
DEFAULT_CHANNELS = ["fill", "market_lifecycle_v2", "orderbook_delta"]


class KalshiWebSocket:
    """WebSocket client for Kalshi private/public channels."""

    def __init__(self, ws_url: str | None = None, api_key_id: str | None = None, private_key_path: str | None = None):
        settings = get_settings()
        self.ws_url = ws_url or settings.kalshi_ws_url
        self.api_key_id = api_key_id or settings.kalshi_api_key_id
        self.private_key_path = private_key_path or settings.kalshi_private_key_path
        self.private_key = load_private_key(self.private_key_path)

        self.websocket: websockets.WebSocketClientProtocol | None = None
        self.connected = False
        self.subscribed_tickers: list[str] = []
        self.callbacks: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None]] = {}
        self._listen_task: asyncio.Task | None = None
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 10

    def _handshake_headers(self) -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        path = "/trade-api/ws/v2"
        signature = sign_request(self.private_key, timestamp, "GET", path)
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "KALSHI-ACCESS-SIGNATURE": signature,
        }

    async def connect(self) -> None:
        """Connect and authenticate WebSocket."""
        headers = self._handshake_headers()
        logger.info("Connecting to Kalshi WebSocket...")
        try:
            self.websocket = await websockets.connect(
                self.ws_url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
            )
            self.connected = True
            self._reconnect_attempts = 0
            logger.info("WebSocket connected")
        except Exception:
            logger.exception("WebSocket connection failed")
            raise

    async def subscribe(self, market_tickers: list[str], channels: list[str] | None = None) -> None:
        """Subscribe to channels for given market tickers."""
        if not self.websocket or not self.connected:
            raise RuntimeError("WebSocket not connected")

        self.subscribed_tickers = list(market_tickers)
        channels = channels or DEFAULT_CHANNELS

        sub_msg = {
            "id": int(time.time() * 1000),
            "cmd": "subscribe",
            "params": {
                "channels": channels,
                "market_tickers": market_tickers,
                "use_yes_price": True,
            },
        }
        await self.websocket.send(json.dumps(sub_msg))
        logger.info("Subscribed to channels %s for %d tickers", channels, len(market_tickers))

    async def listen(self) -> None:
        """Main listen loop with reconnect."""
        while True:
            try:
                await self.connect()
                if self.subscribed_tickers:
                    await self.subscribe(self.subscribed_tickers)
                await self._receive_loop()
            except ConnectionClosed as exc:
                logger.warning("WebSocket closed: %s", exc)
            except Exception:
                logger.exception("WebSocket error")
            finally:
                self.connected = False
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except Exception:
                        pass
                    self.websocket = None

            self._reconnect_attempts += 1
            if self._reconnect_attempts > self._max_reconnect_attempts:
                logger.error("Max WebSocket reconnect attempts reached")
                break

            wait = min(2**self._reconnect_attempts, 60)
            logger.info("Reconnecting in %ds (attempt %d/%d)...", wait, self._reconnect_attempts, self._max_reconnect_attempts)
            await asyncio.sleep(wait)

    async def _receive_loop(self) -> None:
        """Receive and dispatch messages."""
        if not self.websocket:
            return
        async for message in self.websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                logger.warning("Received non-JSON WebSocket message: %s", message)
                continue

            await self._dispatch(data)

    async def _dispatch(self, data: dict[str, Any]) -> None:
        """Route message to registered callback based on type."""
        msg_type = data.get("type") or data.get("msg", {}).get("type") or data.get("channel")
        if not msg_type:
            logger.debug("WebSocket message with no type: %s", data)
            return

        callback = self.callbacks.get(msg_type)
        if callback:
            try:
                result = callback(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Error in WebSocket callback for type %s", msg_type)
        else:
            logger.debug("No callback registered for message type: %s", msg_type)

    def register_callback(self, msg_type: str, callback: Callable[[dict[str, Any]], Coroutine[Any, Any, None] | None]) -> None:
        """Register a callback for a message type."""
        self.callbacks[msg_type] = callback

    async def close(self) -> None:
        """Close connection gracefully."""
        self._max_reconnect_attempts = 0  # Stop reconnect loop
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
