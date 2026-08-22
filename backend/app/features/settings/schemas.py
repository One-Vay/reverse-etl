"""Pydantic schemas for AppSettings."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _strip(value: str | None) -> str | None:
    """A pasted bot token/chat ID with stray leading/trailing whitespace
    (easy to pick up copying from Telegram or a chat app) would otherwise
    be sent to the API verbatim and fail with a confusing "chat not
    found"/401 rather than the obviously-wrong value it actually is."""
    return value.strip() if value is not None else value


class AppSettingsUpdate(BaseModel):
    """Schema for updating settings (all fields optional — partial update)."""

    scheduler_enabled: bool | None = None
    scheduler_poll_interval_seconds: int | None = Field(None, ge=5, le=3600)

    llm_enabled: bool | None = None
    llm_base_url: str | None = Field(None, min_length=1, max_length=500)
    llm_model: str | None = Field(None, min_length=1, max_length=255)

    telegram_enabled: bool | None = None
    telegram_bot_token: str | None = Field(None, max_length=255)
    telegram_chat_id: str | None = Field(None, max_length=255)

    default_connect_timeout_seconds: float | None = Field(None, gt=0, le=300)
    default_request_timeout_seconds: float | None = Field(None, gt=0, le=300)

    _strip_telegram_bot_token = field_validator("telegram_bot_token")(_strip)
    _strip_telegram_chat_id = field_validator("telegram_chat_id")(_strip)


class AppSettingsRead(BaseModel):
    """Schema for reading the current settings."""

    scheduler_enabled: bool
    scheduler_poll_interval_seconds: int

    llm_enabled: bool
    llm_base_url: str
    llm_model: str

    telegram_enabled: bool
    telegram_bot_token: str
    telegram_chat_id: str

    default_connect_timeout_seconds: float
    default_request_timeout_seconds: float

    updated_at: datetime

    model_config = {"from_attributes": True}


class LLMStatus(BaseModel):
    """Whether the configured LLM model is ready to use."""

    model_present: bool
    pulling: bool
    detail: str | None = None


class TelegramTestResult(BaseModel):
    """Result of sending a test message via the Settings page."""

    success: bool
    detail: str | None = None
