"""Application configuration loaded from environment / .env file."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    """Typed settings with validation."""

    kalshi_api_key_id: str = Field(..., alias="KALSHI_API_KEY")
    kalshi_private_key_path: Path = Field(..., alias="KALSHI_PRIVATE_KEY_PATH")
    kalshi_base_url: str = Field(
        default="https://external-api.kalshi.com/trade-api/v2",
        alias="KALSHI_BASE_URL",
    )
    kalshi_ws_url: str = Field(
        default="wss://external-api-ws.kalshi.com/trade-api/ws/v2",
        alias="KALSHI_WS_URL",
    )

    trade_log_path: Path = Field(default=PROJECT_ROOT / "data" / "trades.jsonl", alias="TRADE_LOG_PATH")
    kill_switch_path: Path = Field(default=PROJECT_ROOT / "STOP_BOT", alias="KILL_SWITCH_PATH")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    default_stop_width: float = Field(default=0.15, alias="DEFAULT_STOP_WIDTH")
    default_contracts: int = Field(default=2, alias="DEFAULT_CONTRACTS")
    backup_stop_offset: float = Field(default=0.03, alias="BACKUP_STOP_OFFSET")
    ioc_fallback_buffer: float = Field(default=0.05, alias="IOC_FALLBACK_BUFFER")
    entry_improvement: float = Field(default=0.01, alias="ENTRY_IMPROVEMENT")
    max_window_retries: int = Field(default=5, alias="MAX_WINDOW_RETRIES")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @field_validator("kalshi_private_key_path")
    @classmethod
    def _resolve_key_path(cls, value: Path) -> Path:
        if not value.is_absolute():
            value = PROJECT_ROOT / value
        if not value.exists():
            raise ValueError(f"Kalshi private key not found at {value}")
        return value

    @field_validator("kalshi_api_key_id")
    @classmethod
    def _key_id_nonempty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("KALSHI_API_KEY must be set")
        return value.strip()


def get_settings() -> Settings:
    """Factory returning validated settings."""
    return Settings()
