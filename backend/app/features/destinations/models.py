"""Destination model representing a target CRM (Bitrix24, AmoCRM, etc.)."""

import enum

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.features.syncs.models import Sync


class DestinationType(str, enum.Enum):
    """Supported CRM types."""

    BITRIX24 = "bitrix24"
    AMOCRM = "amocrm"


class Destination(Base, TimestampMixin):
    """
    CRM destination configuration.

    One destination can be used in many syncs (one‑to‑many).
    """

    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User‑friendly unique name",
    )
    type: Mapped[DestinationType] = mapped_column(
        String(50),
        nullable=False,
        doc="CRM type (bitrix24 or amocrm)",
    )
    api_url: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Base API URL (e.g., https://domain.bitrix24.ru/rest/)",
    )
    auth_token: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Authentication token (webhook key or OAuth token)",
    )

    syncs: Mapped[list[Sync]] = relationship(
        back_populates="destination",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Destination(id={self.id}, name='{self.name}')>"
