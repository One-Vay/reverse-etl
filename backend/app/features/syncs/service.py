"""Service layer for Sync entity."""

from datetime import datetime, timezone

import croniter

from app.core.exceptions import NotFoundError, ValidationError
from app.features.destinations.repository import DestinationRepository
from app.features.mappings.repository import MappingRepository
from app.features.sources.repository import SourceRepository
from app.features.syncs.repository import SyncRepository
from app.features.syncs.schemas import (
    SyncCreate,
    SyncListResponse,
    SyncRead,
    SyncUpdate,
)


class SyncService:
    """Business logic for syncs."""

    def __init__(
        self,
        repository: SyncRepository,
        source_repository: SourceRepository,
        destination_repository: DestinationRepository,
        mapping_repository: MappingRepository,
    ):
        self.repository = repository
        self.source_repository = source_repository
        self.destination_repository = destination_repository
        self.mapping_repository = mapping_repository

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
        total = await self.repository.get_count(
            source_id=source_id,
            destination_id=destination_id,
            mapping_id=mapping_id,
            status=status,
            search=search,
        )
        items = await self.repository.get_all(
            skip=skip,
            limit=limit,
            source_id=source_id,
            destination_id=destination_id,
            mapping_id=mapping_id,
            status=status,
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

        # Validate schedule (cron expression)
        if not self._is_valid_cron(data.schedule):
            raise ValidationError(f"Invalid schedule format: '{data.schedule}'")

        # Calculate next_run
        next_run = self._calculate_next_run(data.schedule)

        sync = await self.repository.create(data)
        # Update next_run separately (or include in create)
        if next_run:
            await self.repository.update(sync.id, SyncUpdate(next_run=next_run))
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

        # Validate schedule if provided
        if data.schedule is not None and not self._is_valid_cron(data.schedule):
            raise ValidationError(f"Invalid schedule format: '{data.schedule}'")

        # Calculate next_run if schedule changed
        schedule = data.schedule or existing.schedule
        next_run = self._calculate_next_run(schedule)

        update_dict = data.model_dump(exclude_unset=True)
        if next_run:
            update_dict["next_run"] = next_run

        sync = await self.repository.update(id, SyncUpdate(**update_dict))
        if not sync:
            raise NotFoundError(f"Sync with id {id} not found")
        return SyncRead.model_validate(sync)

    async def delete(self, id: int) -> None:
        deleted = await self.repository.delete(id)
        if not deleted:
            raise NotFoundError(f"Sync with id {id} not found")

    async def run_now(self, id: int) -> None:
        """Manually trigger a sync run (updates last_run and schedules next_run)."""
        sync = await self.repository.get_by_id(id)
        if not sync:
            raise NotFoundError(f"Sync with id {id} not found")

        # Update last_run to now
        now = datetime.now(timezone.utc)
        await self.repository.update_last_run(id, now)

        # Calculate next_run based on schedule
        next_run = self._calculate_next_run(sync.schedule)
        if next_run:
            await self.repository.update(id, SyncUpdate(next_run=next_run))

    @staticmethod
    def _is_valid_cron(schedule: str) -> bool:
        """Check if schedule is a valid cron expression."""
        try:
            croniter.croniter(schedule, datetime.now(timezone.utc))
            return True
        except (ValueError, croniter.CroniterBadCronError):
            return False

    @staticmethod
    def _calculate_next_run(schedule: str) -> datetime | None:
        """Calculate the next run time based on cron schedule."""
        try:
            cron = croniter.croniter(schedule, datetime.utcnow())
            return cron.get_next(datetime)
        except Exception:
            return None
