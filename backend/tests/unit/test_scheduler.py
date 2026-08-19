"""Unit tests for the scheduler's Telegram reporting: delay detection and
message formatting. Repositories and the Telegram client are mocked — no
real DB or network access.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.scheduler import _format_report, _notify, _tick
from app.features.syncs.models import SyncRunStatus


def make_sync(name="Test sync"):
    sync = MagicMock()
    sync.id = 1
    sync.name = name
    return sync


def make_run(*, status=SyncRunStatus.SUCCESS, started_at=None, **overrides):
    run = MagicMock()
    run.status = status
    run.started_at = started_at or datetime.now(timezone.utc)
    run.records_read = overrides.get("records_read", 10)
    run.records_written = overrides.get("records_written", 10)
    run.error_message = overrides.get("error_message", None)
    return run


class TestFormatReport:
    def test_success_report_has_no_delay_warning_when_on_time(self):
        now = datetime.now(timezone.utc)
        run = make_run(started_at=now)
        message = _format_report(make_sync(), run, scheduled_for=now)

        assert "✅" in message
        assert "Read 10 / wrote 10" in message
        assert "late" not in message

    def test_failed_report_includes_the_error(self):
        run = make_run(status=SyncRunStatus.FAILED, error_message="Connection refused")
        message = _format_report(make_sync(), run, scheduled_for=None)

        assert "❌" in message
        assert "Connection refused" in message

    def test_flags_a_run_that_started_well_after_its_scheduled_time(self):
        scheduled_for = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        started_at = scheduled_for + timedelta(hours=3, minutes=10)
        run = make_run(started_at=started_at)

        message = _format_report(make_sync(), run, scheduled_for=scheduled_for)

        assert "⚠️" in message
        assert "3h 10m late" in message
        assert "09:00 UTC" in message

    def test_does_not_flag_a_run_within_normal_poll_jitter(self):
        scheduled_for = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        started_at = scheduled_for + timedelta(minutes=2)
        run = make_run(started_at=started_at)

        message = _format_report(make_sync(), run, scheduled_for=scheduled_for)

        assert "⚠️" not in message


class TestNotify:
    @pytest.mark.asyncio
    async def test_sends_the_formatted_report_via_telegram(self):
        sync = make_sync()
        run = make_run()
        with patch(
            "app.core.scheduler.telegram.send_message", AsyncMock()
        ) as mock_send:
            await _notify("token", "chat-id", sync, run, scheduled_for=run.started_at)

        mock_send.assert_awaited_once()
        args = mock_send.call_args.args
        assert args[0] == "token"
        assert args[1] == "chat-id"
        assert sync.name in args[2]

    @pytest.mark.asyncio
    async def test_a_telegram_failure_does_not_propagate(self):
        from app.core.telegram import TelegramError

        with patch(
            "app.core.scheduler.telegram.send_message",
            AsyncMock(side_effect=TelegramError("boom")),
        ):
            await _notify(
                "token", "chat-id", make_sync(), make_run(), scheduled_for=None
            )


def make_settings(**overrides):
    settings = MagicMock()
    settings.scheduler_poll_interval_seconds = overrides.get("poll_interval", 30)
    settings.scheduler_enabled = overrides.get("scheduler_enabled", True)
    settings.telegram_enabled = overrides.get("telegram_enabled", True)
    settings.telegram_bot_token = overrides.get("telegram_bot_token", "token")
    settings.telegram_chat_id = overrides.get("telegram_chat_id", "chat-id")
    return settings


class TestTick:
    """Covers the restart/catch-up scenario end to end at the orchestration
    level: a sync whose `next_run` passed while the process was down is
    still returned by `get_due()` (its query is a plain `next_run <= now`,
    with no "already missed" bookkeeping to go stale) and, once executed,
    is reported to Telegram with a delay warning."""

    @pytest.mark.asyncio
    async def test_an_overdue_sync_still_fires_and_reports_the_delay_to_telegram(self):
        scheduled_for = datetime.now(timezone.utc) - timedelta(hours=5)
        sync = make_sync()
        sync.next_run = scheduled_for
        run = make_run(started_at=datetime.now(timezone.utc))

        session_cm = AsyncMock()
        session_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
        session_cm.__aexit__ = AsyncMock(return_value=None)

        settings_repo = MagicMock()
        settings_repo.get = AsyncMock(return_value=make_settings())

        sync_repo = MagicMock()
        sync_repo.get_due = AsyncMock(return_value=[sync])

        with (
            patch("app.core.scheduler.AsyncSessionLocal", return_value=session_cm),
            patch("app.core.scheduler.SettingsRepository", return_value=settings_repo),
            patch("app.core.scheduler.SyncRepository", return_value=sync_repo),
            patch(
                "app.core.scheduler.runner.execute", AsyncMock(return_value=run)
            ) as mock_execute,
            patch("app.core.scheduler.telegram.send_message", AsyncMock()) as mock_send,
        ):
            await _tick()

        mock_execute.assert_awaited_once()
        mock_send.assert_awaited_once()
        message = mock_send.call_args.args[2]
        assert "⚠️" in message
        assert "late" in message

    @pytest.mark.asyncio
    async def test_skips_telegram_when_notifications_are_disabled(self):
        sync = make_sync()
        sync.next_run = datetime.now(timezone.utc) - timedelta(hours=1)
        run = make_run()

        session_cm = AsyncMock()
        session_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
        session_cm.__aexit__ = AsyncMock(return_value=None)

        settings_repo = MagicMock()
        settings_repo.get = AsyncMock(
            return_value=make_settings(telegram_enabled=False)
        )

        sync_repo = MagicMock()
        sync_repo.get_due = AsyncMock(return_value=[sync])

        with (
            patch("app.core.scheduler.AsyncSessionLocal", return_value=session_cm),
            patch("app.core.scheduler.SettingsRepository", return_value=settings_repo),
            patch("app.core.scheduler.SyncRepository", return_value=sync_repo),
            patch("app.core.scheduler.runner.execute", AsyncMock(return_value=run)),
            patch("app.core.scheduler.telegram.send_message", AsyncMock()) as mock_send,
        ):
            await _tick()

        mock_send.assert_not_awaited()
