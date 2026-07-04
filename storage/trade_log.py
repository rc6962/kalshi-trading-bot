"""Append-only JSONL trade/event log."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import get_settings

logger = logging.getLogger(__name__)


class TradeLog:
    """Append-only trade/event logger."""

    def __init__(self, path: Path | None = None):
        self.path = path or get_settings().trade_log_path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Append a single event to the log."""
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            **payload,
        }
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception:
            logger.exception("Failed to write trade log event")

    def read_events(self, event_type: str | None = None) -> list[dict[str, Any]]:
        """Read events, optionally filtered by type."""
        events = []
        if not self.path.exists():
            return events
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    if event_type is None or event.get("type") == event_type:
                        events.append(event)
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed trade log line: %s", line)
        return events
