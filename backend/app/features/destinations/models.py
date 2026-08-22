"""Destination model representing a target CRM (Bitrix24, AmoCRM, etc.)."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.features.syncs.models import Sync


class DestinationType(str, enum.Enum):
    """Supported CRM types."""

    BITRIX24 = "bitrix24"
    AMOCRM = "amocrm"


class Destination(Base, TimestampMixin):
    """CRM destination configuration. One destination can be used in many syncs (one-to-many)."""

    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    type: Mapped[DestinationType] = mapped_column(String(50), nullable=False)
    api_url: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_token: Mapped[str] = mapped_column(String(255), nullable=False)

    # Advanced, optional — null means "use the connector's own default"
    # (see e.g. app.connectors.destinations.bitrix24.Bitrix24Connector).
    request_timeout: Mapped[float | None] = mapped_column(Float, nullable=True)

    syncs: Mapped[list["Sync"]] = relationship(
        back_populates="destination",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Destination(id={self.id}, name='{self.name}')>"
