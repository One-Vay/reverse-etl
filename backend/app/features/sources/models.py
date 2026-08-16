"""Source model representing a data source (PostgreSQL, ClickHouse, etc.)."""

import enum

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.features.mappings.models import Mapping


class SourceType(str, enum.Enum):
    """Supported source database types."""

    POSTGRES = "postgres"
    CLICKHOUSE = "clickhouse"


class Source(Base, TimestampMixin):
    """
    Data source configuration.

    One source can have many mappings (one-to-many).
    """

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User‑friendly unique name",
    )
    type: Mapped[SourceType] = mapped_column(
        String(50),
        nullable=False,
        doc="Database type (postgres or clickhouse)",
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    database: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Stored encrypted (service‑layer encryption)",
    )

    # One‑to‑many relationship with Mapping
    mappings: Mapped[list[Mapping]] = relationship(
        back_populates="source",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Source(id={self.id}, name='{self.name}')>"
