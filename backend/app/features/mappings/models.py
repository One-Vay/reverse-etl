"""Mapping model that defines field transformations between source and destination."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.features.sources.models import Source
    from app.features.syncs.models import Sync


class Mapping(Base, TimestampMixin):
    """Field mapping between a source table and a destination CRM entity.

    Each mapping belongs to exactly one source (many-to-one) and can be
    reused in multiple syncs (one-to-many).
    """

    __tablename__ = "mappings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    source_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_table: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_entity: Mapped[str] = mapped_column(String(255), nullable=False)
    field_mappings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    source: Mapped["Source"] = relationship(back_populates="mappings", lazy="selectin")
    syncs: Mapped[list["Sync"]] = relationship(
        back_populates="mapping",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Mapping(id={self.id}, name='{self.name}', source_table='{self.source_table}')>"
