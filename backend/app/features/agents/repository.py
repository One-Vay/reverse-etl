"""Repository for DataAgent and AgentRun entities."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import delete, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.agents.models import AgentRun, AgentRunStatus, AgentStatus, DataAgent
from app.features.agents.schemas import AgentCreate, AgentUpdate


class AgentRepository:
    """CRUD operations for data agents."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> DataAgent | None:
        stmt = select(DataAgent).where(DataAgent.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[DataAgent]:
        stmt = select(DataAgent).offset(skip).limit(limit).order_by(DataAgent.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_count(self) -> int:
        stmt = select(DataAgent)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def create(self, data: AgentCreate) -> DataAgent:
        agent = DataAgent(
            name=data.name,
            destination_id=data.destination_id,
            mapping_id=data.mapping_id,
            goal=data.goal,
            actions=data.actions,
            feature_notes=[note.model_dump() for note in data.feature_notes],
            llm_model=data.llm_model,
            selection_strategy=data.selection_strategy,
            selection_threshold=data.selection_threshold,
            incremental_field=data.incremental_field,
        )
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def update(self, id: int, data: AgentUpdate) -> DataAgent | None:
        update_dict = data.model_dump(exclude_unset=True)
        if "feature_notes" in update_dict and update_dict["feature_notes"] is not None:
            update_dict["feature_notes"] = [
                note if isinstance(note, dict) else note.model_dump()
                for note in update_dict["feature_notes"]
            ]
        if not update_dict:
            return await self.get_by_id(id)
        stmt = (
            update(DataAgent)
            .where(DataAgent.id == id)
            .values(**update_dict)
            .returning(DataAgent)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def update_plan(
        self, id: int, plan: dict[str, Any], generated_at: datetime
    ) -> DataAgent | None:
        """Store a freshly-generated plan and mark the agent READY to run
        — a plan always makes an agent runnable, so this is bundled into
        one server-computed update rather than exposed on `AgentUpdate`."""
        stmt = (
            update(DataAgent)
            .where(DataAgent.id == id)
            .values(
                plan=plan,
                plan_generated_at=generated_at,
                status=AgentStatus.READY,
            )
            .returning(DataAgent)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def update_last_run(self, id: int, last_run_at: datetime) -> DataAgent | None:
        stmt = (
            update(DataAgent)
            .where(DataAgent.id == id)
            .values(last_run_at=last_run_at)
            .returning(DataAgent)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete(self, id: int) -> bool:
        stmt = delete(DataAgent).where(DataAgent.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0  # type: ignore[attr-defined]  # CursorResult at runtime


class AgentRunRepository:
    """CRUD operations for agent runs. Rows are only ever written by
    `app.features.agents.runner`, never via a public create endpoint."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        agent_id: int,
        status: AgentRunStatus,
        started_at: datetime,
        finished_at: datetime | None = None,
        rows_considered: int = 0,
        rows_selected: int = 0,
        rows_written: int = 0,
        selection_summary: str | None = None,
        error_message: str | None = None,
    ) -> AgentRun:
        run = AgentRun(
            agent_id=agent_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            rows_considered=rows_considered,
            rows_selected=rows_selected,
            rows_written=rows_written,
            selection_summary=selection_summary,
            error_message=error_message,
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run, attribute_names=["agent"])
        return run

    async def get_by_agent(
        self, agent_id: int, skip: int = 0, limit: int = 100
    ) -> Sequence[AgentRun]:
        stmt = (
            select(AgentRun)
            .where(AgentRun.agent_id == agent_id)
            .order_by(desc(AgentRun.started_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_agent(self, agent_id: int) -> int:
        stmt = select(AgentRun).where(AgentRun.agent_id == agent_id)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
