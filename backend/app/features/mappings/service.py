"""Service layer for Mapping entity."""

from typing import Optional
from app.features.mappings.repository import MappingRepository
from app.features.sources.repository import SourceRepository
from app.features.mappings.schemas import MappingCreate, MappingUpdate, MappingRead, MappingListResponse
from app.core.exceptions import NotFoundError, ConflictError, ValidationError


class MappingService:
    """Business logic for mappings."""

    def __init__(self, repository: MappingRepository, source_repository: SourceRepository):
        self.repository = repository
        self.source_repository = source_repository

    async def get(self, id: int) -> MappingRead:
        mapping = await self.repository.get_by_id(id)
        if not mapping:
            raise NotFoundError(f"Mapping with id {id} not found")
        return MappingRead.model_validate(mapping)

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
        source_id: Optional[int] = None,
        source_table: Optional[str] = None,
        destination_entity: Optional[str] = None,
    ) -> MappingListResponse:
        total = await self.repository.get_count(
            source_id=source_id,
            source_table=source_table,
            destination_entity=destination_entity,
        )
        items = await self.repository.get_all(
            skip=skip,
            limit=limit,
            source_id=source_id,
            source_table=source_table,
            destination_entity=destination_entity,
        )
        return MappingListResponse(
            items=[MappingRead.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def create(self, data: MappingCreate) -> MappingRead:
        # Validate that source exists
        source = await self.source_repository.get_by_id(data.source_id)
        if not source:
            raise NotFoundError(f"Source with id {data.source_id} not found")

        # Validate field_mappings structure
        if not data.field_mappings:
            raise ValidationError("Field mappings cannot be empty")

        mapping = await self.repository.create(data)
        return MappingRead.model_validate(mapping)

    async def update(self, id: int, data: MappingUpdate) -> MappingRead:
        existing = await self.repository.get_by_id(id)
        if not existing:
            raise NotFoundError(f"Mapping with id {id} not found")

        # If source_id is being updated, validate new source exists
        if data.source_id is not None and data.source_id != existing.source_id:
            source = await self.source_repository.get_by_id(data.source_id)
            if not source:
                raise NotFoundError(f"Source with id {data.source_id} not found")

        mapping = await self.repository.update(id, data)
        if not mapping:
            raise NotFoundError(f"Mapping with id {id} not found")
        return MappingRead.model_validate(mapping)

    async def delete(self, id: int) -> None:
        deleted = await self.repository.delete(id)
        if not deleted:
            raise NotFoundError(f"Mapping with id {id} not found")