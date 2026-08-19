"""Sync model representing a scheduled data transfer job."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.features.destinations.models import Destination
    from app.features.mappings.models import Mapping
    from app.features.sources.models import Source


class SyncStatus(str, enum.Enum):
    """Possible statuses of a sync job."""

    ACTIVE = "active"
    PAUSED = "paused"
    INACTIVE = "inactive"


class IntervalUnit(str, enum.Enum):
    """Granularity of a sync's schedule — deliberately just these two so
    the frequency picker in the UI stays a plain "every N hours/days"
    instead of exposing cron syntax."""

    HOURS = "hours"
    DAYS = "days"


class SyncRunStatus(str, enum.Enum):
    """Outcome of one execution of a sync."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SyncRunTrigger(str, enum.Enum):
    """What caused a sync run to start."""

    MANUAL = "manual"
    SCHEDULED = "scheduled"


class Sync(Base, TimestampMixin):
    """Synchronization job that links a source, a destination, and a mapping.

    Each sync runs on a schedule and transfers data from the source table
    (via the mapping) to the destination CRM entity.
    """

    __tablename__ = "syncs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destination_id: Mapped[int] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mapping_id: Mapped[int] = mapped_column(
        ForeignKey("mappings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    interval_value: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    interval_unit: Mapped[IntervalUnit] = mapped_column(
        String(10), nullable=False, default=IntervalUnit.HOURS
    )
    # "HH:MM", 24h. Only meaningful when interval_unit is DAYS — ignored
    # for HOURS, where a sync just fires every N hours from whenever it
    # was last scheduled.
    run_at_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    incremental_field: Mapped[str | None] = mapped_column(String(255), nullable=True)

    last_run: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_run: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    status: Mapped[SyncStatus] = mapped_column(
        String(20), nullable=False, default=SyncStatus.ACTIVE
    )

    source: Mapped["Source"] = relationship(lazy="selectin")
    destination: Mapped["Destination"] = relationship(
        back_populates="syncs", lazy="selectin"
    )
    mapping: Mapped["Mapping"] = relationship(back_populates="syncs", lazy="selectin")
    runs: Mapped[list["SyncRun"]] = relationship(
        back_populates="sync",
        cascade="all, delete-orphan",
        order_by="SyncRun.started_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<Sync(id={self.id}, name='{self.name}', status='{self.status}')>"


class SyncRun(Base):
    """One execution of a `Sync` — either a manual "Run now" or a
    scheduler-triggered run. Persisted so the dashboard can show real
    history instead of the current run's in-memory result."""

    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    sync_id: Mapped[int] = mapped_column(
        ForeignKey("syncs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[SyncRunStatus] = mapped_column(String(20), nullable=False)
    trigger: Mapped[SyncRunTrigger] = mapped_column(String(20), nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    records_read: Mapped[int] = mapped_column(nullable=False, default=0)
    records_written: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    sync: Mapped["Sync"] = relationship(back_populates="runs", lazy="selectin")

    @property
    def sync_name(self) -> str | None:
        """The owning sync's name, for display without a second lookup —
        exposed so `SyncRunRead.model_validate(run)` can pick it up
        directly via `from_attributes`."""
        return self.sync.name if self.sync is not None else None

    def __repr__(self) -> str:
        return (
            f"<SyncRun(id={self.id}, sync_id={self.sync_id}, status='{self.status}')>"
        )
