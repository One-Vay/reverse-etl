"""Repository for Mapping entity."""

from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.mappings.models import Mapping
from app.features.mappings.schemas import MappingCreate, MappingUpdate


class MappingRepository:
    """CRUD operations for mappings."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> Mapping | None:
        stmt = select(Mapping).where(Mapping.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Mapping | None:
        stmt = select(Mapping).where(Mapping.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        source_id: int | None = None,
        source_table: str | None = None,
        destination_entity: str | None = None,
    ) -> Sequence[Mapping]:
        stmt = select(Mapping)
        if source_id is not None:
            stmt = stmt.where(Mapping.source_id == source_id)
        if source_table:
            stmt = stmt.where(Mapping.source_table == source_table)
        if destination_entity:
            stmt = stmt.where(Mapping.destination_entity == destination_entity)
        stmt = stmt.offset(skip).limit(limit).order_by(Mapping.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_count(
        self,
        source_id: int | None = None,
        source_table: str | None = None,
        destination_entity: str | None = None,
    ) -> int:
        stmt = select(Mapping)
        if source_id is not None:
            stmt = stmt.where(Mapping.source_id == source_id)
        if source_table:
            stmt = stmt.where(Mapping.source_table == source_table)
        if destination_entity:
            stmt = stmt.where(Mapping.destination_entity == destination_entity)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def get_by_source(self, source_id: int) -> Sequence[Mapping]:
        stmt = select(Mapping).where(Mapping.source_id == source_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, data: MappingCreate) -> Mapping:
        mapping = Mapping(
            name=data.name,
            source_id=data.source_id,
            source_table=data.source_table,
            destination_entity=data.destination_entity,
            field_mappings=data.field_mappings,
        )
        self.session.add(mapping)
        await self.session.flush()
        return mapping

    async def update(self, id: int, data: MappingUpdate) -> Mapping | None:
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get_by_id(id)
        stmt = (
            update(Mapping)
            .where(Mapping.id == id)
            .values(**update_dict)
            .returning(Mapping)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        stmt = delete(Mapping).where(Mapping.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0  # type: ignore[attr-defined]  # CursorResult at runtime
