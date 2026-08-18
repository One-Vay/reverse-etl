"""Unit tests for engine construction.

Regression coverage for a real CI failure: `create_async_engine()` was
always called with `pool_size`/`max_overflow`, but those are QueuePool-only
kwargs. SQLite's async driver defaults to NullPool, which rejects them with
a TypeError — this only ever surfaced in CI (pinned SQLAlchemy 2.0.35 with
the sqlite+aiosqlite test DATABASE_URL), never locally against whatever
SQLAlchemy happened to be installed globally, which is exactly why it slipped
through undetected before.
"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import build_engine_kwargs


class TestBuildEngineKwargs:
    def test_omits_pool_kwargs_for_sqlite(self):
        kwargs = build_engine_kwargs(
            "sqlite+aiosqlite:///./test.db",
            debug=False,
            pool_size=5,
            max_overflow=10,
        )
        assert "pool_size" not in kwargs
        assert "max_overflow" not in kwargs
        assert kwargs == {"echo": False}

    def test_includes_pool_kwargs_for_postgres(self):
        kwargs = build_engine_kwargs(
            "postgresql+asyncpg://user:pass@localhost/db",
            debug=True,
            pool_size=5,
            max_overflow=10,
        )
        assert kwargs == {"echo": True, "pool_size": 5, "max_overflow": 10}

    def test_sqlite_kwargs_do_not_raise_on_a_real_engine(self):
        # The actual regression: this call raised TypeError before the fix.
        url = "sqlite+aiosqlite:///:memory:"
        engine = create_async_engine(
            url, **build_engine_kwargs(url, debug=False, pool_size=5, max_overflow=10)
        )
        assert engine is not None

    @pytest.mark.parametrize(
        "url",
        [
            "sqlite+aiosqlite:///./test.db",
            "sqlite:///./test.db",
        ],
    )
    def test_recognizes_sqlite_urls_regardless_of_driver(self, url):
        kwargs = build_engine_kwargs(url, debug=False, pool_size=5, max_overflow=10)
        assert "pool_size" not in kwargs
