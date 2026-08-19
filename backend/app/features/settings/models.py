"""App-level, web-editable operational settings.

Deliberately separate from `app.core.config.Settings` (the env-file-backed
process configuration): infra secrets (`DATABASE_URL`, `SECRET_KEY`,
`ENCRYPTION_KEY`) stay in `.env` and require a restart to change, by
design — they gate what the process can even start with. Everything in
*this* table is operational behavior a user should be able to tune from
the web console without redeploying: the scheduler's cadence and the
optional local-LLM mapping-suggestion feature.

Modeled as a single row (`id` fixed at 1) rather than a generic key/value
table — the field set is small and known ahead of time, so a real schema
gives type safety and validation for free.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin

# The one row this table ever has.
SINGLETON_ID = 1


class AppSettings(Base, TimestampMixin):
    """Singleton row of web-editable application settings."""

    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True)

    scheduler_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    scheduler_poll_interval_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )

    llm_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    llm_base_url: Mapped[str] = mapped_column(
        String(500), nullable=False, default="http://ollama:11434"
    )
    llm_model: Mapped[str] = mapped_column(
        String(255), nullable=False, default="qwen2.5:0.5b"
    )

    default_connect_timeout_seconds: Mapped[float] = mapped_column(
        Float, nullable=False, default=10.0
    )
    default_request_timeout_seconds: Mapped[float] = mapped_column(
        Float, nullable=False, default=30.0
    )

    def __repr__(self) -> str:
        return f"<AppSettings(scheduler_enabled={self.scheduler_enabled}, llm_enabled={self.llm_enabled})>"
