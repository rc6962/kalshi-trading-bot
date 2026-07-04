"""Tests for orderbook parsing and maker-price logic."""

from decimal import Decimal

from kalshi.orderbook import compute_maker_entry_prices, parse_orderbook


def sample_orderbook() -> dict:
    return {
        "orderbook_fp": {
            "yes_dollars": [
                ["0.0100", "100.00"],
                ["0.3000", "50.00"],
                ["0.3100", "25.00"],
            ],
            "no_dollars": [
                ["0.0100", "100.00"],
                ["0.6200", "50.00"],
                ["0.6300", "25.00"],
            ],
        }
    }


def test_parse_orderbook() -> None:
    parsed = parse_orderbook(sample_orderbook())
    assert parsed["yes_bid"] == Decimal("0.3100")
    assert parsed["yes_ask"] == Decimal("0.3700")  # 1.00 - 0.6300
    assert parsed["no_bid"] == Decimal("0.6300")
    assert parsed["no_ask"] == Decimal("0.6900")  # 1.00 - 0.3100


def test_compute_maker_entry_prices_wide_spread() -> None:
    parsed = parse_orderbook(sample_orderbook())
    maker = compute_maker_entry_prices(parsed, improvement=Decimal("0.01"))
    # Spread is 0.06 (0.37 - 0.31) >= 2*0.01, so improve by 1 cent
    assert maker["yes_bid_maker"] == Decimal("0.3200")  # improve bid
    assert maker["yes_ask_maker"] == Decimal("0.3600")  # improve ask


def test_compute_maker_entry_prices_tight_spread() -> None:
    ob = {
        "orderbook_fp": {
            "yes_dollars": [["0.4900", "100.00"], ["0.5000", "50.00"]],
            "no_dollars": [["0.4900", "100.00"], ["0.5000", "50.00"]],
        }
    }
    parsed = parse_orderbook(ob)
    maker = compute_maker_entry_prices(parsed, improvement=Decimal("0.01"))
    # Spread is 0.02 (0.50 - 0.50? wait yes_bid=0.50, yes_ask=0.50) => join
    assert maker["joined"] is True
    assert maker["yes_bid_maker"] == Decimal("0.5000")
    assert maker["yes_ask_maker"] == Decimal("0.5000")
