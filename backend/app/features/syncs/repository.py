"""Repository for Sync entity."""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.syncs.models import (
    Sync,
    SyncRun,
    SyncRunStatus,
    SyncRunTrigger,
    SyncStatus,
)
from app.features.syncs.schemas import SyncCreate, SyncUpdate


class SyncRepository:
    """CRUD operations for syncs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> Sync | None:
        stmt = select(Sync).where(Sync.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Sync | None:
        stmt = select(Sync).where(Sync.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        source_id: int | None = None,
        destination_id: int | None = None,
        mapping_id: int | None = None,
        status: SyncStatus | None = None,
        search: str | None = None,
    ) -> Sequence[Sync]:
        stmt = select(Sync)
        filters = []
        if source_id is not None:
            filters.append(Sync.source_id == source_id)
        if destination_id is not None:
            filters.append(Sync.destination_id == destination_id)
        if mapping_id is not None:
            filters.append(Sync.mapping_id == mapping_id)
        if status is not None:
            filters.append(Sync.status == status)
        if search:
            filters.append(Sync.name.ilike(f"%{search}%"))
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.offset(skip).limit(limit).order_by(Sync.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_count(
        self,
        source_id: int | None = None,
        destination_id: int | None = None,
        mapping_id: int | None = None,
        status: SyncStatus | None = None,
        search: str | None = None,
    ) -> int:
        stmt = select(Sync)
        filters = []
        if source_id is not None:
            filters.append(Sync.source_id == source_id)
        if destination_id is not None:
            filters.append(Sync.destination_id == destination_id)
        if mapping_id is not None:
            filters.append(Sync.mapping_id == mapping_id)
        if status is not None:
            filters.append(Sync.status == status)
        if search:
            filters.append(Sync.name.ilike(f"%{search}%"))
        if filters:
            stmt = stmt.where(and_(*filters))
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def get_by_source(self, source_id: int) -> Sequence[Sync]:
        stmt = select(Sync).where(Sync.source_id == source_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_destination(self, destination_id: int) -> Sequence[Sync]:
        stmt = select(Sync).where(Sync.destination_id == destination_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_mapping(self, mapping_id: int) -> Sequence[Sync]:
        stmt = select(Sync).where(Sync.mapping_id == mapping_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active(self) -> Sequence[Sync]:
        stmt = select(Sync).where(Sync.status == SyncStatus.ACTIVE)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_due(self, now: datetime) -> Sequence[Sync]:
        """Active syncs whose `next_run` has arrived — what the scheduler
        picks up on each poll, regardless of how overdue: a sync whose
        `next_run` passed while the process was down is still returned
        here on the very first poll after restart."""
        stmt = select(Sync).where(
            Sync.status == SyncStatus.ACTIVE,
            Sync.next_run.is_not(None),
            Sync.next_run <= now,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, data: SyncCreate) -> Sync:
        sync = Sync(
            name=data.name,
            source_id=data.source_id,
            destination_id=data.destination_id,
            mapping_id=data.mapping_id,
            interval_value=data.interval_value,
            interval_unit=data.interval_unit,
            run_at_time=data.run_at_time,
            incremental_field=data.incremental_field,
            status=data.status,
        )
        self.session.add(sync)
        await self.session.flush()
        return sync

    async def update(self, id: int, data: SyncUpdate) -> Sync | None:
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get_by_id(id)
        stmt = update(Sync).where(Sync.id == id).values(**update_dict).returning(Sync)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        stmt = delete(Sync).where(Sync.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0  # type: ignore[attr-defined]  # CursorResult at runtime

    async def update_last_run(self, id: int, last_run: datetime) -> Sync | None:
        stmt = (
            update(Sync).where(Sync.id == id).values(last_run=last_run).returning(Sync)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def update_next_run(self, id: int, next_run: datetime) -> Sync | None:
        stmt = (
            update(Sync).where(Sync.id == id).values(next_run=next_run).returning(Sync)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()


class SyncRunRepository:
    """CRUD operations for sync runs. Rows are only ever written by
    `app.features.syncs.runner`, never via a public create endpoint."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        sync_id: int,
        status: SyncRunStatus,
        trigger: SyncRunTrigger,
        started_at: datetime,
        finished_at: datetime | None = None,
        records_read: int = 0,
        records_written: int = 0,
        error_message: str | None = None,
    ) -> SyncRun:
        run = SyncRun(
            sync_id=sync_id,
            status=status,
            trigger=trigger,
            started_at=started_at,
            finished_at=finished_at,
            records_read=records_read,
            records_written=records_written,
            error_message=error_message,
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run, attribute_names=["sync"])
        return run

    async def get_by_sync(
        self, sync_id: int, skip: int = 0, limit: int = 100
    ) -> Sequence[SyncRun]:
        stmt = (
            select(SyncRun)
            .where(SyncRun.sync_id == sync_id)
            .order_by(desc(SyncRun.started_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_sync(self, sync_id: int) -> int:
        stmt = select(SyncRun).where(SyncRun.sync_id == sync_id)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[SyncRun]:
        stmt = (
            select(SyncRun).order_by(desc(SyncRun.started_at)).offset(skip).limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_all(self) -> int:
        stmt = select(SyncRun)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
