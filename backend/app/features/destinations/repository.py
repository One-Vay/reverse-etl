"""Repository for Destination entity."""

from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.destinations.models import Destination
from app.features.destinations.schemas import DestinationCreate, DestinationUpdate


class DestinationRepository:
    """CRUD operations for destinations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> Destination | None:
        stmt = select(Destination).where(Destination.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Destination | None:
        stmt = select(Destination).where(Destination.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        name: str | None = None,
        type: str | None = None,
    ) -> Sequence[Destination]:
        stmt = select(Destination)
        if name:
            stmt = stmt.where(Destination.name.ilike(f"%{name}%"))
        if type:
            stmt = stmt.where(Destination.type == type)
        stmt = stmt.offset(skip).limit(limit).order_by(Destination.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_count(self, name: str | None = None, type: str | None = None) -> int:
        stmt = select(Destination)
        if name:
            stmt = stmt.where(Destination.name.ilike(f"%{name}%"))
        if type:
            stmt = stmt.where(Destination.type == type)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def create(self, data: DestinationCreate) -> Destination:
        dest = Destination(
            name=data.name,
            type=data.type,
            api_url=data.api_url,
            auth_token=data.auth_token.get_secret_value(),
        )
        self.session.add(dest)
        await self.session.flush()
        return dest

    async def update(self, id: int, data: DestinationUpdate) -> Destination | None:
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get_by_id(id)

        if "auth_token" in update_dict and update_dict["auth_token"] is not None:
            update_dict["auth_token"] = update_dict["auth_token"].get_secret_value()

        stmt = (
            update(Destination)
            .where(Destination.id == id)
            .values(**update_dict)
            .returning(Destination)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        stmt = delete(Destination).where(Destination.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
