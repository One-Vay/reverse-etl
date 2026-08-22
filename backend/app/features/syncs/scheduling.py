"""Interval scheduling helpers shared between `SyncService` (computing a
new/updated sync's first `next_run`), `runner`/the background scheduler
(advancing `next_run` after each execution), and the upcoming-runs
calendar (projecting future fire times) — split out of `service.py` so
`runner.py` can use them without importing the service module and
creating an import cycle.

Deliberately just "every N hours" or "every N days at HH:MM" — no cron.
A UI-only user can't debug a bad cron expression; they can always tell
you what "every 6 hours" or "daily at 9am" means.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from app.features.syncs.models import IntervalUnit

_DEFAULT_RUN_AT_TIME = "09:00"


def _parse_time(value: str) -> tuple[int, int]:
    hour_str, _, minute_str = value.partition(":")
    return int(hour_str), int(minute_str)


def calculate_next_run(
    interval_value: int,
    interval_unit: IntervalUnit,
    run_at_time: str | None,
    *,
    anchor: datetime,
) -> datetime:
    """The next fire time after `anchor`.

    `anchor` should be the sync's *previously scheduled* `next_run` when
    advancing after a real execution (not the actual, possibly-late,
    execution time) — anchoring to the schedule rather than to whenever
    the run actually happened is what keeps the cadence from drifting,
    and is what makes "this run was late" a meaningful comparison
    afterwards. For a brand-new or just-edited sync, `anchor` is simply
    "now".
    """
    if interval_unit == IntervalUnit.HOURS:
        return anchor + timedelta(hours=interval_value)

    hour, minute = _parse_time(run_at_time or _DEFAULT_RUN_AT_TIME)
    candidate = anchor.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= anchor:
        candidate += timedelta(days=interval_value)
    return candidate


def project_occurrences(
    interval_value: int,
    interval_unit: IntervalUnit,
    run_at_time: str | None,
    *,
    starting_from: datetime,
    within: timedelta,
) -> list[datetime]:
    """Every future fire time from `starting_from` (inclusive) up to
    `starting_from + within` — powers the upcoming-runs calendar. Caller
    passes the sync's current `next_run` as `starting_from`."""
    if within <= timedelta(0):
        return []

    horizon = starting_from + within
    occurrences: list[datetime] = []
    current = starting_from
    # Bounded so a misconfigured interval (e.g. 0) can't spin forever.
    for _ in range(1000):
        if current > horizon:
            break
        occurrences.append(current)
        current = calculate_next_run(
            interval_value, interval_unit, run_at_time, anchor=current
        )
    return occurrences
