"""Pydantic schemas for AppSettings."""

from datetime import datetime

from pydantic import BaseModel, Field


class AppSettingsUpdate(BaseModel):
    """Schema for updating settings (all fields optional — partial update)."""

    scheduler_enabled: bool | None = None
    scheduler_poll_interval_seconds: int | None = Field(None, ge=5, le=3600)

    llm_enabled: bool | None = None
    llm_base_url: str | None = Field(None, min_length=1, max_length=500)
    llm_model: str | None = Field(None, min_length=1, max_length=255)

    default_connect_timeout_seconds: float | None = Field(None, gt=0, le=300)
    default_request_timeout_seconds: float | None = Field(None, gt=0, le=300)


class AppSettingsRead(BaseModel):
    """Schema for reading the current settings."""

    scheduler_enabled: bool
    scheduler_poll_interval_seconds: int

    llm_enabled: bool
    llm_base_url: str
    llm_model: str

    default_connect_timeout_seconds: float
    default_request_timeout_seconds: float

    updated_at: datetime

    model_config = {"from_attributes": True}


class LLMStatus(BaseModel):
    """Whether the configured LLM model is ready to use."""

    model_present: bool
    pulling: bool
    detail: str | None = None
