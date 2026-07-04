"""PDF report generator for bot performance."""

import io
import logging
from datetime import date
from decimal import Decimal
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image

from reporting.metrics import build_trades, compute_metrics, compute_trade_fees, compute_trade_pnl
from storage.trade_log import TradeLog

logger = logging.getLogger(__name__)


def _style_table(table: Table) -> None:
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#333333")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f5f5f5")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )


def _daily_pnl_chart(daily_pnl: dict[str, Decimal]) -> Image:
    """Generate a cumulative PnL chart and return as reportlab Image."""
    sorted_days = sorted(daily_pnl.keys())
    cumulative = []
    running = Decimal("0")
    for day in sorted_days:
        running += daily_pnl[day]
        cumulative.append(float(running))

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(sorted_days, cumulative, marker="o", linewidth=2)
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative PnL ($)")
    ax.set_title("Daily Cumulative PnL")
    fig.autofmt_xdate()
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    buf.seek(0)
    plt.close(fig)
    return Image(buf, width=5.5 * inch, height=2.75 * inch)


def generate_pdf_report(start_date: date, end_date: date, output_path: str) -> None:
    """Generate a PDF report for the given date range."""
    trade_log = TradeLog()
    events = trade_log.read_events()

    # Filter events by date range
    filtered = []
    for event in events:
        ts = event.get("ts", "")
        try:
            event_date = date.fromisoformat(ts[:10])
        except ValueError:
            continue
        if start_date <= event_date <= end_date:
            filtered.append(event)

    trades = build_trades(filtered)
    metrics = compute_metrics(trades)

    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Kalshi 15-Min Window Bot Report", styles["Title"]))
    story.append(Paragraph(f"{start_date} to {end_date}", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * inch))

    # Summary table
    summary_data = [
        ["Metric", "Value"],
        ["Total Trades", str(metrics["total_trades"])],
        ["Gross PnL", f"${metrics['total_pnl']:.2f}"],
        ["Total Fees", f"${metrics['total_fees']:.2f}"],
        ["Net PnL", f"${metrics['net_pnl']:.2f}"],
        ["Wins", str(metrics["wins"])],
        ["Losses", str(metrics["losses"])],
        ["Win Rate", f"{metrics['win_rate']*100:.1f}%"],
        ["Max Drawdown", f"${metrics['max_drawdown']:.2f}"],
    ]
    summary_table = Table(summary_data)
    _style_table(summary_table)
    story.append(summary_table)
    story.append(Spacer(1, 0.3 * inch))

    # Per-asset PnL
    if metrics["per_asset_pnl"]:
        story.append(Paragraph("Per-Asset Net PnL", styles["Heading3"]))
        asset_data = [["Asset", "Net PnL"]]
        for asset, pnl in metrics["per_asset_pnl"].items():
            asset_data.append([asset, f"${pnl:.2f}"])
        asset_table = Table(asset_data)
        _style_table(asset_table)
        story.append(asset_table)
        story.append(Spacer(1, 0.3 * inch))

    # Daily PnL
    if metrics["daily_pnl"]:
        story.append(Paragraph("Daily Net PnL", styles["Heading3"]))
        day_data = [["Date", "Net PnL"]]
        for day, pnl in sorted(metrics["daily_pnl"].items()):
            day_data.append([day, f"${pnl:.2f}"])
        day_table = Table(day_data)
        _style_table(day_table)
        story.append(day_table)
        story.append(Spacer(1, 0.3 * inch))

        # Chart
        story.append(_daily_pnl_chart(metrics["daily_pnl"]))
        story.append(Spacer(1, 0.3 * inch))

    # Trade list
    if trades:
        story.append(Paragraph("Trade List", styles["Heading3"]))
        trade_data = [["Opened", "Asset", "Side", "Entry", "Exit", "Count", "Reason", "Net"]]
        for trade in trades:
            net = compute_trade_pnl(trade) - compute_trade_fees(trade)
            trade_data.append(
                [
                    trade.opened_at.strftime("%Y-%m-%d %H:%M"),
                    trade.asset,
                    trade.side,
                    f"${trade.entry_price:.2f}",
                    f"${trade.exit_price:.2f}",
                    f"{trade.count:.2f}",
                    trade.exit_reason,
                    f"${net:.2f}",
                ]
            )
        trade_table = Table(trade_data, repeatRows=1)
        _style_table(trade_table)
        story.append(trade_table)

    doc.build(story)
    logger.info("PDF report generated: %s", output_path)
