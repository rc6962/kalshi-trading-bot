"""Tests for order manager stop logic."""

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from kalshi.order_manager import OrderManager


class MockRestClient:
    def __init__(self):
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self.responses: list[dict[str, Any]] = []
        self.response_index = 0

    def post(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append(("POST", path, json_data))
        count = str(json_data.get("count", "0")) if json_data else "0"
        response = {"order_id": f"order-{self.response_index}", "fill_count": count}
        self.response_index += 1
        return response

    def delete(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append(("DELETE", path, json_data))
        return {}


def test_place_entry_and_ioc_stop() -> None:
    rest = MockRestClient()
    om = OrderManager(rest)

    entry = om.place_entry(
        ticker="KXBTC15M-TEST",
        asset="BTC",
        side="bid",
        price=Decimal("0.5000"),
        count=Decimal("2.00"),
        stop_width=Decimal("0.15"),
    )
    assert entry.order_id == "order-0"

    om.on_entry_fill(entry.order_id, None, "0.5000", "2.00", "maker")

    # Should have placed entry and then one IoC stop
    assert len(rest.calls) == 2
    method, path, payload = rest.calls[1]
    assert method == "POST"
    assert path == "/portfolio/events/orders"
    assert payload is not None
    assert payload["time_in_force"] == "immediate_or_cancel"
    assert payload["reduce_only"] is True
    assert payload["side"] == "ask"
    # Stop price = entry - stop_width - buffer
    # 0.50 - 0.15 - 0.05 = 0.30
    assert Decimal(payload["price"]) == Decimal("0.3000")


def test_no_stop_price_clamped() -> None:
    rest = MockRestClient()
    om = OrderManager(rest)

    entry = om.place_entry(
        ticker="KXBTC15M-TEST",
        asset="BTC",
        side="ask",
        price=Decimal("0.9000"),
        count=Decimal("2.00"),
        stop_width=Decimal("0.15"),
    )
    om.on_entry_fill(entry.order_id, None, "0.9000", "2.00", "maker")

    _, _, payload = rest.calls[1]
    assert payload["side"] == "bid"
    # 0.90 + 0.15 + 0.05 = 1.10, clamped to 0.99
    assert Decimal(payload["price"]) == Decimal("0.9900")


def test_on_settlement_clears_state() -> None:
    rest = MockRestClient()
    om = OrderManager(rest)

    entry = om.place_entry(
        ticker="KXBTC15M-TEST",
        asset="BTC",
        side="bid",
        price=Decimal("0.5000"),
        count=Decimal("2.00"),
        stop_width=Decimal("0.15"),
    )
    om.on_entry_fill(entry.order_id, None, "0.5000", "2.00", "maker")
    assert len(om.entries) == 1

    om.on_settlement("KXBTC15M-TEST", "yes", "0.9900")
    assert len(om.entries) == 0
    assert "KXBTC15M-TEST" in om.settled_tickers
