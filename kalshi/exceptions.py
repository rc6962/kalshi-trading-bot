"""Kalshi API exception types."""


class KalshiError(Exception):
    """Base Kalshi API error."""

    def __init__(self, message: str, status_code: int | None = None, response_body: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body or {}


class KalshiAuthError(KalshiError):
    """401 or authentication failure."""


class KalshiRateLimitError(KalshiError):
    """429 too many requests."""


class KalshiOrderError(KalshiError):
    """Order placement/reconciliation error."""


class KalshiMarketError(KalshiError):
    """Market not found or inactive."""
