"""Executes one `Sync`: reads from its source, transforms rows through its
mapping, writes to its destination, and records the outcome as a
`SyncRun`. This is the one place "Run now" (`SyncService.run_now`) and the
background scheduler (`app.core.scheduler`) both funnel through.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import ConnectorError
from app.features.destinations.repository import DestinationRepository
from app.features.destinations.service import DestinationService
from app.features.mappings.transform import transform_row
from app.features.sources.repository import SourceRepository
from app.features.sources.service import SourceService
from app.features.syncs.models import Sync, SyncRun, SyncRunStatus, SyncRunTrigger
from app.features.syncs.repository import SyncRepository, SyncRunRepository
from app.features.syncs.scheduling import calculate_next_run


async def execute(
    sync: Sync, *, session: AsyncSession, trigger: SyncRunTrigger
) -> SyncRun:
    """Run one sync end-to-end and persist the result as a `SyncRun`.

    Never raises for a connector-level failure (network/auth/missing
    table/entity) — that's recorded as a failed `SyncRun` instead, so a
    broken sync doesn't crash the scheduler loop or the "Run now" request.
    `last_run`/`next_run` are updated either way, so a failing sync is
    retried on its normal schedule instead of hot-looping.
    """
    started_at = datetime.now(timezone.utc)
    sync_repo = SyncRepository(session)
    run_repo = SyncRunRepository(session)

    records_read = 0
    records_written = 0
    error_message: str | None = None

    try:
        mapping = sync.mapping

        source_service = SourceService(SourceRepository(session))
        source_connector = await source_service.build_connector(sync.source_id)
        async with source_connector:
            rows = await source_connector.fetch_data(
                mapping.source_table, where=_incremental_where(sync)
            )
        records_read = len(rows)

        records = [transform_row(row, mapping.field_mappings) for row in rows]

        destination_service = DestinationService(DestinationRepository(session))
        destination_connector = await destination_service.build_connector(
            sync.destination_id
        )
        async with destination_connector:
            records_written = await destination_connector.upsert_data(
                mapping.destination_entity, records
            )

        status = SyncRunStatus.SUCCESS
    except ConnectorError as exc:
        status = SyncRunStatus.FAILED
        error_message = str(exc)
    except Exception as exc:  # noqa: BLE001 - a broken sync must not crash the caller
        status = SyncRunStatus.FAILED
        error_message = f"Unexpected error: {exc}"

    finished_at = datetime.now(timezone.utc)
    run = await run_repo.create(
        sync_id=sync.id,
        status=status,
        trigger=trigger,
        started_at=started_at,
        finished_at=finished_at,
        records_read=records_read,
        records_written=records_written,
        error_message=error_message,
    )

    await sync_repo.update_last_run(sync.id, finished_at)
    # Anchored to the sync's own previous next_run (not `finished_at`/`now`)
    # so a late run doesn't push every future occurrence later too — the
    # cadence tracks the original schedule, not when runs actually happen.
    # If the sync was overdue by more than one interval (e.g. the
    # container was down for a while), step forward until the result is
    # actually in the future instead of landing on another already-past
    # time — otherwise the very next scheduler tick would see it as due
    # again and fire a burst of catch-up runs instead of just the one.
    next_run = calculate_next_run(
        sync.interval_value,
        sync.interval_unit,
        sync.run_at_time,
        anchor=sync.next_run or finished_at,
    )
    while next_run <= finished_at:
        next_run = calculate_next_run(
            sync.interval_value, sync.interval_unit, sync.run_at_time, anchor=next_run
        )
    await sync_repo.update_next_run(sync.id, next_run)

    return run


def _incremental_where(sync: Sync) -> str | None:
    """A `WHERE` clause that only reads rows newer than the last run, for
    syncs with `incremental_field` configured. Falls back to a full-table
    read on the very first run (no `last_run` yet) or when incremental
    sync isn't configured."""
    if not sync.incremental_field or not sync.last_run:
        return None
    watermark = sync.last_run.isoformat()
    return f"{sync.incremental_field} > '{watermark}'"
