"""In-process background loop that triggers due syncs on their schedule.

No task queue (Celery/Redis/etc.) — this app runs as a single process
(see `backend/Dockerfile`/`entrypoint.sh`), so a plain `asyncio` loop
polling the database is simpler and sufficient at this scale. Started
from `app.main`'s lifespan and cancelled cleanly on shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core import telegram
from app.core.database import AsyncSessionLocal
from app.features.settings.repository import SettingsRepository
from app.features.syncs import runner
from app.features.syncs.models import Sync, SyncRun, SyncRunStatus, SyncRunTrigger
from app.features.syncs.repository import SyncRepository

logger = logging.getLogger(__name__)

# Floor for the poll interval even if a misconfigured/corrupt settings row
# somehow has a lower value — keeps a broken setting from turning this into
# a tight loop hammering the database.
_MIN_POLL_INTERVAL_SECONDS = 5.0

# How much lateness is normal poll jitter vs. worth flagging to the user —
# e.g. a container restart that caused a scheduled run to be missed and
# picked up late on the next tick after startup.
_LATE_TOLERANCE = timedelta(minutes=5)


async def run_forever() -> None:
    """The scheduler's main loop. Runs until its task is cancelled."""
    logger.info("Scheduler started")
    try:
        while True:
            interval = await _tick()
            await asyncio.sleep(max(interval, _MIN_POLL_INTERVAL_SECONDS))
    except asyncio.CancelledError:
        logger.info("Scheduler stopped")
        raise


async def _tick() -> float:
    """Run one poll: check settings, execute any due syncs, and return how
    long to sleep before the next poll."""
    async with AsyncSessionLocal() as session:
        settings = await SettingsRepository(session).get()
        # get() may have created the default row — persist that.
        await session.commit()
        interval = settings.scheduler_poll_interval_seconds
        enabled = settings.scheduler_enabled
        telegram_enabled = settings.telegram_enabled
        telegram_bot_token = settings.telegram_bot_token
        telegram_chat_id = settings.telegram_chat_id

    if not enabled:
        return interval

    async with AsyncSessionLocal() as session:
        sync_repo = SyncRepository(session)
        due = await sync_repo.get_due(datetime.now(timezone.utc))
        for sync in due:
            # Captured before execute() runs — execute() immediately
            # advances next_run for the *following* cycle, so this is the
            # only place the originally-scheduled time is still available
            # for delay detection.
            scheduled_for = sync.next_run
            try:
                run = await runner.execute(
                    sync, session=session, trigger=SyncRunTrigger.SCHEDULED
                )
                await session.commit()
            except Exception:
                # runner.execute() already turns connector failures into a
                # failed SyncRun rather than raising — this only catches a
                # genuinely unexpected bug, so one broken sync can't stop
                # every other due sync in the same tick from running.
                logger.exception("Scheduled run of sync %s crashed", sync.id)
                await session.rollback()
                continue

            if telegram_enabled and telegram_bot_token and telegram_chat_id:
                await _notify(
                    telegram_bot_token, telegram_chat_id, sync, run, scheduled_for
                )

    return interval


async def _notify(
    bot_token: str,
    chat_id: str,
    sync: Sync,
    run: SyncRun,
    scheduled_for: datetime | None,
) -> None:
    """Report a completed scheduled run to Telegram. Never lets a broken
    Telegram integration affect the sync run it's reporting on."""
    try:
        await telegram.send_message(
            bot_token, chat_id, _format_report(sync, run, scheduled_for)
        )
    except telegram.TelegramError:
        logger.exception("Failed to send Telegram report for sync %s", sync.id)


def _format_report(sync: Sync, run: SyncRun, scheduled_for: datetime | None) -> str:
    ok = run.status == SyncRunStatus.SUCCESS
    lines = [
        f"{'✅' if ok else '❌'} <b>{sync.name}</b>",
        f"Read {run.records_read} / wrote {run.records_written} records"
        if ok
        else f"Failed: {run.error_message or 'unknown error'}",
    ]
    if scheduled_for is not None:
        delay = run.started_at - scheduled_for
        if delay > _LATE_TOLERANCE:
            due_str = scheduled_for.strftime("%H:%M UTC")
            lines.append(f"⚠️ Ran {_format_delay(delay)} late (was due at {due_str})")
    return "\n".join(lines)


def _format_delay(delay: timedelta) -> str:
    total_minutes = int(delay.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"
