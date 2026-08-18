"""Database engine, session factory, and base model classes."""

from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


def build_engine_kwargs(
    database_url: str, *, debug: bool, pool_size: int, max_overflow: int
) -> dict[str, object]:
    """Build the kwargs for `create_async_engine()`.

    `pool_size`/`max_overflow` only apply to `QueuePool` (used for Postgres).
    SQLite's async driver defaults to `NullPool`, which doesn't accept either
    kwarg and raises `TypeError` if given them — so they're only included for
    non-SQLite URLs (e.g. the sqlite+aiosqlite URL used in tests and CI).
    """
    kwargs: dict[str, object] = {"echo": debug}
    if not database_url.startswith("sqlite"):
        kwargs["pool_size"] = pool_size
        kwargs["max_overflow"] = max_overflow
    return kwargs


engine = create_async_engine(
    settings.DATABASE_URL,
    **build_engine_kwargs(
        settings.DATABASE_URL,
        debug=settings.DEBUG,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
    ),
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class TimestampMixin:
    """Adds created_at and updated_at timestamps to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that yields a database session.

    Commits on success, rolls back on failure, and always closes the session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
