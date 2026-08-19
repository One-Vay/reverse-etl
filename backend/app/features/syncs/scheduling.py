"""Cron helpers shared between `SyncService` (validating a sync's schedule)
and `runner`/the background scheduler (computing when it next runs) — split
out of `service.py` so `runner.py` can use them without importing the
service module and creating an import cycle.
"""

from __future__ import annotations

from datetime import datetime, timezone

import croniter


def is_valid_cron(schedule: str) -> bool:
    """Check if `schedule` is a valid cron expression."""
    try:
        croniter.croniter(schedule, datetime.now(timezone.utc))
        return True
    except (ValueError, croniter.CroniterBadCronError):
        return False


def calculate_next_run(schedule: str) -> datetime | None:
    """Compute the next UTC run time for a cron expression, or `None` if
    `schedule` isn't valid."""
    try:
        cron = croniter.croniter(schedule, datetime.now(timezone.utc))
        return cron.get_next(datetime)
    except Exception:
        return None
