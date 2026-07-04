"""PnL / performance metrics from trade log."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Position:
    ticker: str
    asset: str
    side: str  # "bid"=long YES, "ask"=long NO
    entry_price: Decimal
    count: Decimal
    opened_at: datetime
    closed_count: Decimal = Decimal("0")


@dataclass
class Trade:
    ticker: str
    asset: str
    side: str
    entry_price: Decimal
    exit_price: Decimal
    count: Decimal
    opened_at: datetime
    closed_at: datetime
    exit_reason: str  # "stop_fill" or "settlement"


def _parse_ts(ts: str) -> datetime:
    ts = ts.replace("Z", "+00:00")
    return datetime.fromisoformat(ts)


def _fee_taker(price: Decimal, count: Decimal, multiplier: Decimal = Decimal("0.07")) -> Decimal:
    """Confirmed Kalshi crypto taker fee formula."""
    raw = multiplier * price * (Decimal("1") - price) * count
    # Round to cents
    return raw.quantize(Decimal("0.01"))


def _fee_maker() -> Decimal:
    """Maker fees round to $0.00 for retail sizes."""
    return Decimal("0")


def build_trades(events: list[dict[str, Any]]) -> list[Trade]:
    """Reconstruct closed trades from trade log events."""
    open_positions: dict[str, list[Position]] = defaultdict(list)
    trades: list[Trade] = []

    for event in events:
        etype = event.get("type")
        ts = _parse_ts(event["ts"])

        if etype == "fill":
            # Entry fill
            ticker = event["ticker"]
            asset = event["asset"]
            side = event["side"]
            entry_price = Decimal(event["fill_price"])
            fill_count = Decimal(event["fill_count"])
            pos = Position(
                ticker=ticker,
                asset=asset,
                side=side,
                entry_price=entry_price,
                count=fill_count,
                opened_at=ts,
            )
            open_positions[ticker].append(pos)

        elif etype == "stop_fill":
            ticker = event["ticker"]
            exit_price = Decimal(event["fill_price"])
            fill_count = Decimal(event["fill_count"])
            _close_position(open_positions, ticker, exit_price, fill_count, ts, "stop_fill", trades)

        elif etype == "settlement":
            ticker = event["ticker"]
            result = event.get("result")
            settlement_price = Decimal(event.get("settlement_price", "0.99") if result == "yes" else "0.00")
            _close_position(open_positions, ticker, settlement_price, None, ts, "settlement", trades)

    return trades


def _close_position(
    open_positions: dict[str, list[Position]],
    ticker: str,
    exit_price: Decimal,
    count: Decimal | None,
    closed_at: datetime,
    reason: str,
    trades: list[Trade],
) -> None:
    """Close open positions FIFO."""
    positions = open_positions.get(ticker, [])
    if not positions:
        return

    remaining = count
    while positions and (remaining is None or remaining > Decimal("0")):
        pos = positions[0]
        close_count = pos.count - pos.closed_count
        if remaining is not None:
            close_count = min(close_count, remaining)
        if close_count <= Decimal("0"):
            positions.pop(0)
            continue

        pos.closed_count += close_count
        if pos.closed_count >= pos.count:
            positions.pop(0)

        trades.append(
            Trade(
                ticker=ticker,
                asset=pos.asset,
                side=pos.side,
                entry_price=pos.entry_price,
                exit_price=exit_price,
                count=close_count,
                opened_at=pos.opened_at,
                closed_at=closed_at,
                exit_reason=reason,
            )
        )
        if remaining is not None:
            remaining -= close_count


def compute_trade_pnl(trade: Trade) -> Decimal:
    """Compute gross PnL for a single closed trade (before fees)."""
    if trade.side == "bid":
        # Long YES: buy at entry, sell/expire at exit
        return (trade.exit_price - trade.entry_price) * trade.count
    else:
        # Long NO (short YES): sell at entry, buy back/expire at exit
        return (trade.entry_price - trade.exit_price) * trade.count


def compute_trade_fees(trade: Trade) -> Decimal:
    """Compute approximate fees for a trade."""
    # With the current execution design, entries are post_only maker and exits are IoC taker.
    entry_fee = _fee_maker()
    exit_fee = _fee_taker(trade.exit_price, trade.count)
    return entry_fee + exit_fee


def compute_metrics(trades: list[Trade]) -> dict[str, Any]:
    """Compute summary metrics from closed trades."""
    if not trades:
        return {
            "total_trades": 0,
            "total_pnl": Decimal("0"),
            "total_fees": Decimal("0"),
            "net_pnl": Decimal("0"),
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "max_drawdown": Decimal("0"),
        }

    gross_pnl = Decimal("0")
    total_fees = Decimal("0")
    wins = 0
    losses = 0
    per_asset: dict[str, Decimal] = defaultdict(Decimal)
    daily_pnl: dict[str, Decimal] = defaultdict(Decimal)

    for trade in trades:
        pnl = compute_trade_pnl(trade)
        fees = compute_trade_fees(trade)
        net = pnl - fees
        gross_pnl += pnl
        total_fees += fees
        if net > 0:
            wins += 1
        elif net < 0:
            losses += 1
        per_asset[trade.asset] += net
        day = trade.closed_at.strftime("%Y-%m-%d")
        daily_pnl[day] += net

    total = wins + losses
    win_rate = wins / total if total > 0 else 0.0

    # Max drawdown from daily PnL series
    sorted_days = sorted(daily_pnl.keys())
    cumulative = Decimal("0")
    peak = Decimal("0")
    max_dd = Decimal("0")
    for day in sorted_days:
        cumulative += daily_pnl[day]
        peak = max(peak, cumulative)
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

    return {
        "total_trades": len(trades),
        "total_pnl": gross_pnl,
        "total_fees": total_fees,
        "net_pnl": gross_pnl - total_fees,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "per_asset_pnl": dict(per_asset),
        "daily_pnl": dict(daily_pnl),
        "max_drawdown": max_dd,
    }
