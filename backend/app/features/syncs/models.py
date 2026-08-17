"""Sync model representing a scheduled data transfer job."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
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

    schedule: Mapped[str] = mapped_column(String(100), nullable=False)
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

    def __repr__(self) -> str:
        return f"<Sync(id={self.id}, name='{self.name}', status='{self.status}')>"
