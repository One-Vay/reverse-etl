"""Unit tests for the scheduler's per-tick logic, with the DB session and
runner fully mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core import scheduler
from app.features.syncs.models import SyncRunTrigger


def make_settings(enabled=True, interval=30):
    settings = MagicMock()
    settings.scheduler_enabled = enabled
    settings.scheduler_poll_interval_seconds = interval
    return settings


def make_session_cm(session: MagicMock) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm


class TestTick:
    @pytest.mark.asyncio
    async def test_returns_the_configured_interval(self):
        settings_repo = MagicMock()
        settings_repo.get = AsyncMock(return_value=make_settings(interval=45))
        sync_repo = MagicMock()
        sync_repo.get_due = AsyncMock(return_value=[])
        session = MagicMock()
        session.commit = AsyncMock()

        with (
            patch(
                "app.core.scheduler.AsyncSessionLocal",
                return_value=make_session_cm(session),
            ),
            patch("app.core.scheduler.SettingsRepository", return_value=settings_repo),
            patch("app.core.scheduler.SyncRepository", return_value=sync_repo),
        ):
            interval = await scheduler._tick()

        assert interval == 45

    @pytest.mark.asyncio
    async def test_skips_due_syncs_when_scheduler_disabled(self):
        settings_repo = MagicMock()
        settings_repo.get = AsyncMock(return_value=make_settings(enabled=False))
        session = MagicMock()
        session.commit = AsyncMock()

        with (
            patch(
                "app.core.scheduler.AsyncSessionLocal",
                return_value=make_session_cm(session),
            ),
            patch("app.core.scheduler.SettingsRepository", return_value=settings_repo),
            patch("app.core.scheduler.SyncRepository") as mock_sync_repo_cls,
        ):
            await scheduler._tick()

        mock_sync_repo_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_executes_every_due_sync(self):
        settings_repo = MagicMock()
        settings_repo.get = AsyncMock(return_value=make_settings(enabled=True))

        sync_a = MagicMock(id=1)
        sync_b = MagicMock(id=2)
        sync_repo = MagicMock()
        sync_repo.get_due = AsyncMock(return_value=[sync_a, sync_b])

        session = MagicMock()
        session.commit = AsyncMock()

        with (
            patch(
                "app.core.scheduler.AsyncSessionLocal",
                return_value=make_session_cm(session),
            ),
            patch("app.core.scheduler.SettingsRepository", return_value=settings_repo),
            patch("app.core.scheduler.SyncRepository", return_value=sync_repo),
            patch("app.core.scheduler.runner.execute", AsyncMock()) as mock_execute,
        ):
            await scheduler._tick()

        assert mock_execute.await_count == 2
        for call, sync in zip(mock_execute.await_args_list, [sync_a, sync_b]):
            assert call.args[0] is sync
            assert call.kwargs["trigger"] == SyncRunTrigger.SCHEDULED

    @pytest.mark.asyncio
    async def test_one_crashing_sync_does_not_stop_the_others(self):
        settings_repo = MagicMock()
        settings_repo.get = AsyncMock(return_value=make_settings(enabled=True))

        sync_a = MagicMock(id=1)
        sync_b = MagicMock(id=2)
        sync_repo = MagicMock()
        sync_repo.get_due = AsyncMock(return_value=[sync_a, sync_b])

        session = MagicMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        with (
            patch(
                "app.core.scheduler.AsyncSessionLocal",
                return_value=make_session_cm(session),
            ),
            patch("app.core.scheduler.SettingsRepository", return_value=settings_repo),
            patch("app.core.scheduler.SyncRepository", return_value=sync_repo),
            patch(
                "app.core.scheduler.runner.execute",
                AsyncMock(side_effect=[RuntimeError("boom"), None]),
            ) as mock_execute,
        ):
            await scheduler._tick()

        assert mock_execute.await_count == 2
