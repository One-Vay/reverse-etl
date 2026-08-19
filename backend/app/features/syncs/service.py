"""Service layer for Sync entity."""

from datetime import datetime, timedelta, timezone

from app.core.exceptions import NotFoundError, ValidationError
from app.features.destinations.repository import DestinationRepository
from app.features.mappings.repository import MappingRepository
from app.features.sources.repository import SourceRepository
from app.features.syncs import runner
from app.features.syncs.models import SyncRunTrigger, SyncStatus
from app.features.syncs.repository import SyncRepository, SyncRunRepository
from app.features.syncs.scheduling import calculate_next_run, project_occurrences
from app.features.syncs.schemas import (
    SyncCreate,
    SyncListResponse,
    SyncRead,
    SyncRunListResponse,
    SyncRunRead,
    SyncUpdate,
    UpcomingSyncRuns,
)


def _parse_status(status: str | None) -> SyncStatus | None:
    if status is None:
        return None
    try:
        return SyncStatus(status)
    except ValueError:
        valid = ", ".join(s.value for s in SyncStatus)
        raise ValidationError(f"Invalid status '{status}'. Must be one of: {valid}")


class SyncService:
    """Business logic for syncs."""

    def __init__(
        self,
        repository: SyncRepository,
        source_repository: SourceRepository,
        destination_repository: DestinationRepository,
        mapping_repository: MappingRepository,
        run_repository: SyncRunRepository,
    ):
        self.repository = repository
        self.source_repository = source_repository
        self.destination_repository = destination_repository
        self.mapping_repository = mapping_repository
        self.run_repository = run_repository

    async def get(self, id: int, load_relations: bool = True) -> SyncRead:
        sync = await self.repository.get_by_id(id)
        if not sync:
            raise NotFoundError(f"Sync with id {id} not found")
        return SyncRead.model_validate(sync)

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
        source_id: int | None = None,
        destination_id: int | None = None,
        mapping_id: int | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> SyncListResponse:
        parsed_status = _parse_status(status)
        total = await self.repository.get_count(
            source_id=source_id,
            destination_id=destination_id,
            mapping_id=mapping_id,
            status=parsed_status,
            search=search,
        )
        items = await self.repository.get_all(
            skip=skip,
            limit=limit,
            source_id=source_id,
            destination_id=destination_id,
            mapping_id=mapping_id,
            status=parsed_status,
            search=search,
        )
        return SyncListResponse(
            items=[SyncRead.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def create(self, data: SyncCreate) -> SyncRead:
        # Validate foreign keys exist
        source = await self.source_repository.get_by_id(data.source_id)
        if not source:
            raise NotFoundError(f"Source with id {data.source_id} not found")

        destination = await self.destination_repository.get_by_id(data.destination_id)
        if not destination:
            raise NotFoundError(f"Destination with id {data.destination_id} not found")

        mapping = await self.mapping_repository.get_by_id(data.mapping_id)
        if not mapping:
            raise NotFoundError(f"Mapping with id {data.mapping_id} not found")

        # Validate that mapping belongs to the same source
        if mapping.source_id != data.source_id:
            raise ValidationError(
                f"Mapping {data.mapping_id} does not belong to source {data.source_id}"
            )

        next_run = calculate_next_run(
            data.interval_value,
            data.interval_unit,
            data.run_at_time,
            anchor=datetime.now(timezone.utc),
        )

        sync = await self.repository.create(data)
        sync = await self.repository.update_next_run(sync.id, next_run) or sync
        return SyncRead.model_validate(sync)

    async def update(self, id: int, data: SyncUpdate) -> SyncRead:
        existing = await self.repository.get_by_id(id)
        if not existing:
            raise NotFoundError(f"Sync with id {id} not found")

        # Validate foreign keys if updated
        if data.source_id is not None:
            source = await self.source_repository.get_by_id(data.source_id)
            if not source:
                raise NotFoundError(f"Source with id {data.source_id} not found")

        if data.destination_id is not None:
            destination = await self.destination_repository.get_by_id(
                data.destination_id
            )
            if not destination:
                raise NotFoundError(
                    f"Destination with id {data.destination_id} not found"
                )

        if data.mapping_id is not None:
            mapping = await self.mapping_repository.get_by_id(data.mapping_id)
            if not mapping:
                raise NotFoundError(f"Mapping with id {data.mapping_id} not found")
            # If source_id also changed, validate mapping-source consistency
            source_id = data.source_id or existing.source_id
            if mapping.source_id != source_id:
                raise ValidationError(
                    f"Mapping {data.mapping_id} does not belong to source {source_id}"
                )

        schedule_changed = (
            data.interval_value is not None
            or data.interval_unit is not None
            or data.run_at_time is not None
        )

        sync = await self.repository.update(id, data)
        if not sync:
            raise NotFoundError(f"Sync with id {id} not found")

        # Recalculate next_run if the schedule changed. Kept as a separate
        # update_next_run() call (like update_last_run()) rather than a field
        # on SyncUpdate, since next_run is server-computed, not part of the
        # public update payload.
        if schedule_changed:
            next_run = calculate_next_run(
                sync.interval_value,
                sync.interval_unit,
                sync.run_at_time,
                anchor=datetime.now(timezone.utc),
            )
            sync = await self.repository.update_next_run(id, next_run) or sync

        return SyncRead.model_validate(sync)

    async def delete(self, id: int) -> None:
        deleted = await self.repository.delete(id)
        if not deleted:
            raise NotFoundError(f"Sync with id {id} not found")

    async def run_now(self, id: int) -> SyncRunRead:
        """Manually trigger a sync run: actually reads the source, applies
        the mapping, and writes to the destination (see `runner.execute`),
        then persists the outcome as a `SyncRun`.

        Raises:
            NotFoundError: If the sync doesn't exist.
        """
        sync = await self.repository.get_by_id(id)
        if not sync:
            raise NotFoundError(f"Sync with id {id} not found")

        run = await runner.execute(
            sync,
            session=self.repository.session,
            trigger=SyncRunTrigger.MANUAL,
        )
        return SyncRunRead.model_validate(run)

    async def get_runs(
        self, id: int, skip: int = 0, limit: int = 100
    ) -> SyncRunListResponse:
        """Raises NotFoundError if the sync doesn't exist."""
        sync = await self.repository.get_by_id(id)
        if not sync:
            raise NotFoundError(f"Sync with id {id} not found")

        total = await self.run_repository.count_by_sync(id)
        items = await self.run_repository.get_by_sync(id, skip=skip, limit=limit)
        return SyncRunListResponse(
            items=[SyncRunRead.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_all_runs(
        self, skip: int = 0, limit: int = 100
    ) -> SyncRunListResponse:
        total = await self.run_repository.count_all()
        items = await self.run_repository.get_all(skip=skip, limit=limit)
        return SyncRunListResponse(
            items=[SyncRunRead.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def get_upcoming(self, days: int = 7) -> list[UpcomingSyncRuns]:
        """Projected fire times for every active sync over the next `days`
        days, for the dashboard's upcoming-runs calendar."""
        active = await self.repository.get_active()
        within = timedelta(days=days)
        return [
            UpcomingSyncRuns(
                sync_id=sync.id,
                sync_name=sync.name,
                occurrences=project_occurrences(
                    sync.interval_value,
                    sync.interval_unit,
                    sync.run_at_time,
                    starting_from=sync.next_run,
                    within=within,
                ),
            )
            for sync in active
            if sync.next_run is not None
        ]
