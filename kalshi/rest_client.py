"""Authenticated Kalshi REST client with retry/backoff."""

import json
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives.asymmetric import rsa

from config.settings import get_settings
from kalshi.auth import load_private_key, sign_request
from kalshi.exceptions import KalshiAuthError, KalshiError, KalshiMarketError, KalshiOrderError, KalshiRateLimitError

logger = logging.getLogger(__name__)


class KalshiRestClient:
    """Thin wrapper around requests with Kalshi auth and retries."""

    def __init__(self, base_url: str | None = None, api_key_id: str | None = None, private_key_path: Path | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.kalshi_base_url).rstrip("/")
        parsed = urlparse(self.base_url)
        self.base_path = parsed.path or "/trade-api/v2"
        self.api_key_id = api_key_id or settings.kalshi_api_key_id
        self.private_key_path = private_key_path or settings.kalshi_private_key_path
        self.private_key: rsa.RSAPrivateKey = load_private_key(self.private_key_path)
        self.session = requests.Session()

    def _headers(self, method: str, path: str) -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        signature = sign_request(self.private_key, timestamp, method, path)
        return {
            "KALSHI-ACCESS-KEY": self.api_key_id,
            "KALSHI-ACCESS-TIMESTAMP": timestamp,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        if not path.startswith("/"):
            path = "/" + path
        full_url = self.base_url + path
        sign_path = self.base_path + path

        # First attempt uses initial headers
        headers = self._headers(method, sign_path)

        last_exception: Exception | None = None
        for attempt in range(max_retries + 1):
            # Regenerate headers on each retry so timestamp is never stale
            if attempt > 0:
                headers = self._headers(method, sign_path)

            try:
                response = self.session.request(
                    method=method,
                    url=full_url,
                    headers=headers,
                    params=params,
                    json=json_data,
                    timeout=30,
                )
            except requests.RequestException as exc:
                last_exception = exc
                logger.warning("Request failed (attempt %d/%d): %s", attempt + 1, max_retries + 1, exc)
                if attempt < max_retries:
                    time.sleep(2**attempt)
                    continue
                raise KalshiError(f"Network error after {max_retries + 1} attempts: {exc}") from exc

            status = response.status_code
            try:
                body = response.json() if response.content else {}
            except json.JSONDecodeError:
                body = {"raw": response.text}

            if status == 200 or status == 201:
                return body
            if status == 204:
                return {}
            if status == 401:
                raise KalshiAuthError("Authentication failed", status, body)
            if status == 429:
                wait = 2**attempt
                logger.warning("Rate limited (429). Backing off %ds...", wait)
                if attempt < max_retries:
                    time.sleep(wait)
                    continue
                raise KalshiRateLimitError("Rate limit exceeded", status, body)
            if status == 404:
                raise KalshiMarketError(f"Market or resource not found: {path}", status, body)
            if status == 400 or status == 409:
                raise KalshiOrderError(f"Order error ({status}): {body}", status, body)

            # 5xx retry
            if 500 <= status < 600 and attempt < max_retries:
                logger.warning("Server error %s (attempt %d/%d)", status, attempt + 1, max_retries + 1)
                time.sleep(2**attempt)
                continue

            raise KalshiError(f"Kalshi API error {status}: {body}", status, body)

        raise KalshiError(f"Max retries exceeded: {last_exception}")

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", path, params=params)

    def post(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("POST", path, json_data=json_data)

    def delete(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("DELETE", path, json_data=json_data)

    def get_balance(self) -> dict[str, Any]:
        return self.get("/portfolio/balance")

    def get_positions(self) -> dict[str, Any]:
        return self.get("/portfolio/positions")

    def get_orders(self, status: str | None = None) -> dict[str, Any]:
        params = {}
        if status:
            params["status"] = status
        return self.get("/portfolio/events/orders", params=params)

    def get_market(self, ticker: str) -> dict[str, Any]:
        return self.get(f"/markets/{ticker}")

    def get_markets(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.get("/markets", params=params or {})

    def get_orderbook(self, ticker: str) -> dict[str, Any]:
        return self.get(f"/markets/{ticker}/orderbook")
