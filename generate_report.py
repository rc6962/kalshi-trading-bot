"""Generate PDF performance report for a date range."""

import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from reporting.pdf_report import generate_pdf_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Kalshi bot PDF report")
    parser.add_argument("--start", required=True, type=_parse_date, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, type=_parse_date, help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--output",
        type=str,
        help="Output PDF path",
    )
    args = parser.parse_args()

    if args.start > args.end:
        logger.error("Start date must be before or equal to end date")
        sys.exit(1)

    output = args.output or f"report_{args.start}_to_{args.end}.pdf"

    generate_pdf_report(args.start, args.end, output)
    print(f"Report saved to: {Path(output).resolve()}")


if __name__ == "__main__":
    main()
