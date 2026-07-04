"""Risk controls: kill switch, daily loss cap, balance checks."""

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any

from config.settings import get_settings
from kalshi.rest_client import KalshiRestClient

logger = logging.getLogger(__name__)


class RiskGuard:
    """Collection of runtime safety checks."""

    def __init__(self, rest: KalshiRestClient | None = None, kill_switch_path: Path | None = None):
        self.rest = rest
        self.kill_switch_path = kill_switch_path or get_settings().kill_switch_path

    def kill_switch_active(self) -> bool:
        """Return True if STOP_BOT file exists."""
        return self.kill_switch_path.exists()

    def check_daily_loss(self, current_daily_pnl: float, cap: float | None) -> bool:
        """Return True if trading should halt due to daily loss cap."""
        if not cap or cap <= 0:
            return False
        if current_daily_pnl <= -cap:
            logger.warning("Daily loss cap reached: pnl=%.2f, cap=-%.2f", current_daily_pnl, cap)
            return True
        return False

    def check_balance(self, estimated_max_loss: float) -> bool:
        """Return True if balance is sufficient for estimated max loss."""
        if self.rest is None:
            return True
        try:
            balance_data = self.rest.get_balance()
            balance_cents = balance_data.get("balance", 0)
            balance = float(balance_cents) / 100.0
            if balance < estimated_max_loss:
                logger.warning(
                    "Insufficient balance: %.2f available, %.2f required",
                    balance,
                    estimated_max_loss,
                )
                return False
            return True
        except Exception:
            logger.exception("Failed to check balance")
            return False

    def check_exchange_status(self) -> bool:
        """Return True if exchange is open for trading."""
        if self.rest is None:
            return True
        try:
            status = self.rest.get("/exchange/status")
            trading = status.get("exchange_active", False) or status.get("trading_active", False)
            if not trading:
                logger.warning("Exchange not active: %s", status)
            return trading
        except Exception:
            logger.exception("Failed to check exchange status")
            return False


def estimated_max_loss_for_window(planned_entries: list[dict[str, Any]]) -> float:
    """Compute worst-case dollar loss for a set of planned entries.

    For a YES-long entry at price p: max loss = p * contracts.
    For a NO-long entry (= short YES) at price p: max loss = (1 - p) * contracts.
    """
    total = Decimal("0")
    for entry in planned_entries:
        side = entry["side"].lower()
        price = Decimal(str(entry["price"]))
        count = Decimal(str(entry["count"]))
        if side == "bid":
            # buy YES
            total += price * count
        elif side == "ask":
            # sell YES = long NO; max loss if settles at 1.00
            total += (Decimal("1.00") - price) * count
        else:
            raise ValueError(f"Unknown side: {side}")
    return float(total)
