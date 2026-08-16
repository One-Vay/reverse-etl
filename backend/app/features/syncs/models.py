"""Sync model representing a scheduled data transfer job."""

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.features.destinations.models import Destination
from app.features.mappings.models import Mapping
from app.features.sources.models import Source


class SyncStatus(str, enum.Enum):
    """Possible statuses of a sync job."""

    ACTIVE = "active"
    PAUSED = "paused"
    INACTIVE = "inactive"


class Sync(Base, TimestampMixin):
    """
    Synchronization job that links a source, a destination, and a mapping.

    Each sync runs on a schedule and transfers data from the source table
    (via the mapping) to the destination CRM entity.
    """

    __tablename__ = "syncs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User‑friendly sync name",
    )

    # Foreign keys with cascade delete
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

    schedule: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Cron expression ('*/30 * * * *') or interval text ('30 minutes')",
    )
    incremental_field: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Column name used for incremental loading (e.g., 'updated_at')",
    )

    last_run: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of the last successful run",
    )
    next_run: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Estimated next run time",
    )

    status: Mapped[SyncStatus] = mapped_column(
        String(20),
        nullable=False,
        default=SyncStatus.ACTIVE,
        doc="Current sync status",
    )

    # Relationships
    source: Mapped[Source] = relationship(lazy="selectin")
    destination: Mapped[Destination] = relationship(
        back_populates="syncs",
        lazy="selectin",
    )
    mapping: Mapped[Mapping] = relationship(
        back_populates="syncs",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Sync(id={self.id}, name='{self.name}', status='{self.status}')>"
