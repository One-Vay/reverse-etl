"""Repository for Source entity."""

from typing import Optional, Sequence
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.sources.models import Source
from app.features.sources.schemas import SourceCreate, SourceUpdate


class SourceRepository:
    """CRUD operations for sources."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> Optional[Source]:
        stmt = select(Source).where(Source.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Source]:
        stmt = select(Source).where(Source.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None,
        type: Optional[str] = None,
    ) -> Sequence[Source]:
        stmt = select(Source)
        if name:
            stmt = stmt.where(Source.name.ilike(f"%{name}%"))
        if type:
            stmt = stmt.where(Source.type == type)
        stmt = stmt.offset(skip).limit(limit).order_by(Source.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_count(self, name: Optional[str] = None, type: Optional[str] = None) -> int:
        stmt = select(Source)
        if name:
            stmt = stmt.where(Source.name.ilike(f"%{name}%"))
        if type:
            stmt = stmt.where(Source.type == type)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def create(self, data: SourceCreate) -> Source:
        source = Source(
            name=data.name,
            type=data.type,
            host=data.host,
            port=data.port,
            database=data.database,
            username=data.username,
            password=data.password.get_secret_value(),
        )
        self.session.add(source)
        await self.session.flush()
        return source

    async def update(self, id: int, data: SourceUpdate) -> Optional[Source]:
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get_by_id(id)

        if "password" in update_dict and update_dict["password"] is not None:
            update_dict["password"] = update_dict["password"].get_secret_value()

        stmt = (
            update(Source)
            .where(Source.id == id)
            .values(**update_dict)
            .returning(Source)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        stmt = delete(Source).where(Source.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0