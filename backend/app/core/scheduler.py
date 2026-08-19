"""In-process background loop that triggers due syncs on their schedule.

No task queue (Celery/Redis/etc.) — this app runs as a single process
(see `backend/Dockerfile`/`entrypoint.sh`), so a plain `asyncio` loop
polling the database is simpler and sufficient at this scale. Started
from `app.main`'s lifespan and cancelled cleanly on shutdown.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.core.database import AsyncSessionLocal
from app.features.settings.repository import SettingsRepository
from app.features.syncs import runner
from app.features.syncs.models import SyncRunTrigger
from app.features.syncs.repository import SyncRepository

logger = logging.getLogger(__name__)

# Floor for the poll interval even if a misconfigured/corrupt settings row
# somehow has a lower value — keeps a broken setting from turning this into
# a tight loop hammering the database.
_MIN_POLL_INTERVAL_SECONDS = 5.0


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

    if not enabled:
        return interval

    async with AsyncSessionLocal() as session:
        sync_repo = SyncRepository(session)
        due = await sync_repo.get_due(datetime.now(timezone.utc))
        for sync in due:
            try:
                await runner.execute(
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

    return interval
