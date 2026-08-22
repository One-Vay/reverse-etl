"""Service layer for DataAgent: CRUD, LLM plan generation, running the
selection+sync pipeline, and per-agent local-LLM model management (list
what's installed on Ollama, pull a new one by name)."""

from __future__ import annotations

import asyncio
import logging

from app.core import llm, telegram
from app.core.exceptions import NotFoundError, ValidationError
from app.features.agents import runner
from app.features.agents.models import AgentRun, AgentRunStatus, AgentStatus, DataAgent
from app.features.agents.planner import generate_plan as _generate_plan
from app.features.agents.repository import AgentRepository, AgentRunRepository
from app.features.agents.schemas import (
    AgentCreate,
    AgentListResponse,
    AgentRead,
    AgentRunListResponse,
    AgentRunRead,
    AgentUpdate,
    FeatureNote,
    LLMModelStatus,
)
from app.features.destinations.repository import DestinationRepository
from app.features.mappings.repository import MappingRepository
from app.features.settings.repository import SettingsRepository
from app.features.sources.repository import SourceRepository
from app.features.sources.service import SourceService

logger = logging.getLogger(__name__)

# Small sample handed to the planner for context — just enough for the
# LLM to see what the data actually looks like, not the whole table.
_PLAN_SAMPLE_ROWS = 20

# Whether a model pull is currently in flight, keyed by (base_url, model).
# Process-local, in-memory, mirroring
# `app.features.settings.service._pulling` — deliberately not persisted,
# since this app runs as a single process.
_pulling: set[tuple[str, str]] = set()


class AgentService:
    """Business logic for data agents."""

    def __init__(
        self,
        repository: AgentRepository,
        destination_repository: DestinationRepository,
        mapping_repository: MappingRepository,
        run_repository: AgentRunRepository,
        settings_repository: SettingsRepository,
    ):
        self.repository = repository
        self.destination_repository = destination_repository
        self.mapping_repository = mapping_repository
        self.run_repository = run_repository
        self.settings_repository = settings_repository

    async def get(self, id: int) -> AgentRead:
        agent = await self.repository.get_by_id(id)
        if not agent:
            raise NotFoundError(f"Agent with id {id} not found")
        return AgentRead.model_validate(agent)

    async def get_list(self, skip: int = 0, limit: int = 100) -> AgentListResponse:
        total = await self.repository.get_count()
        items = await self.repository.get_all(skip=skip, limit=limit)
        return AgentListResponse(
            items=[AgentRead.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def create(self, data: AgentCreate) -> AgentRead:
        await self._validate_references(data.destination_id, data.mapping_id)
        agent = await self.repository.create(data)
        return AgentRead.model_validate(agent)

    async def update(self, id: int, data: AgentUpdate) -> AgentRead:
        existing = await self.repository.get_by_id(id)
        if not existing:
            raise NotFoundError(f"Agent with id {id} not found")

        await self._validate_references(data.destination_id, data.mapping_id)

        agent = await self.repository.update(id, data)
        if not agent:
            raise NotFoundError(f"Agent with id {id} not found")
        return AgentRead.model_validate(agent)

    async def delete(self, id: int) -> None:
        deleted = await self.repository.delete(id)
        if not deleted:
            raise NotFoundError(f"Agent with id {id} not found")

    async def _validate_references(
        self, destination_id: int | None, mapping_id: int | None
    ) -> None:
        if destination_id is not None:
            destination = await self.destination_repository.get_by_id(destination_id)
            if not destination:
                raise NotFoundError(f"Destination with id {destination_id} not found")
        if mapping_id is not None:
            mapping = await self.mapping_repository.get_by_id(mapping_id)
            if not mapping:
                raise NotFoundError(f"Mapping with id {mapping_id} not found")

    async def generate_plan(self, id: int) -> AgentRead:
        """Ask the agent's configured LLM to analyze its goal against the
        source table's schema and a small data sample, then store the
        result and mark the agent READY to run.

        Raises:
            NotFoundError: If the agent doesn't exist.
            ValidationError: If the LLM is unreachable or its response
                couldn't be parsed into a usable plan.
        """
        agent = await self.repository.get_by_id(id)
        if not agent:
            raise NotFoundError(f"Agent with id {id} not found")

        app_settings = await self.settings_repository.get()
        if not app_settings.llm_enabled:
            raise ValidationError(
                "AI mapping suggestions must be enabled in Settings before "
                "generating a plan — agents use the same local LLM."
            )

        mapping = agent.mapping
        source_service = SourceService(SourceRepository(self.repository.session))
        columns = await source_service.get_table_schema(
            mapping.source_id, mapping.source_table, "public"
        )
        sample_rows = await source_service.preview_table(
            mapping.source_id, mapping.source_table, "public", None, _PLAN_SAMPLE_ROWS
        )

        feature_notes = [FeatureNote(**note) for note in agent.feature_notes]
        plan = await _generate_plan(
            goal=agent.goal,
            actions=agent.actions,
            table_name=mapping.source_table,
            columns=columns,
            feature_notes=feature_notes,
            sample_rows=sample_rows,
            model=agent.llm_model,
            base_url=app_settings.llm_base_url,
        )

        agent = (
            await self.repository.update_plan(
                id, plan.model_dump(mode="json"), plan.generated_at
            )
            or agent
        )
        return AgentRead.model_validate(agent)

    async def run_now(self, id: int) -> AgentRunRead:
        """Run the agent's selection+sync pipeline immediately (see
        `app.features.agents.runner.execute`), then report the outcome to
        Telegram if notifications are enabled — mirrors
        `app.core.scheduler`'s reporting for scheduled syncs, just
        triggered manually rather than on a schedule.

        Raises:
            NotFoundError: If the agent doesn't exist.
            ValidationError: If the agent has no plan yet.
        """
        agent = await self.repository.get_by_id(id)
        if not agent:
            raise NotFoundError(f"Agent with id {id} not found")
        if agent.status == AgentStatus.DRAFT or not agent.plan:
            raise ValidationError("Generate a plan for this agent before running it.")

        run = await runner.execute(agent, session=self.repository.session)

        app_settings = await self.settings_repository.get()
        if (
            app_settings.telegram_enabled
            and app_settings.telegram_bot_token
            and app_settings.telegram_chat_id
        ):
            await self._notify_telegram(
                app_settings.telegram_bot_token,
                app_settings.telegram_chat_id,
                agent,
                run,
            )

        return AgentRunRead.model_validate(run)

    @staticmethod
    async def _notify_telegram(
        bot_token: str, chat_id: str, agent: DataAgent, run: AgentRun
    ) -> None:
        try:
            await telegram.send_message(
                bot_token, chat_id, _format_agent_report(agent, run)
            )
        except telegram.TelegramError:
            logger.exception("Failed to send Telegram report for agent %s", agent.id)

    async def get_runs(
        self, id: int, skip: int = 0, limit: int = 100
    ) -> AgentRunListResponse:
        agent = await self.repository.get_by_id(id)
        if not agent:
            raise NotFoundError(f"Agent with id {id} not found")

        total = await self.run_repository.count_by_agent(id)
        items = await self.run_repository.get_by_agent(id, skip=skip, limit=limit)
        return AgentRunListResponse(
            items=[AgentRunRead.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def list_llm_models(self) -> list[str]:
        """Models already pulled onto the configured Ollama server, for
        the agent form's model picker.

        Raises:
            ValidationError: If Ollama can't be reached.
        """
        app_settings = await self.settings_repository.get()
        try:
            return await llm.list_models(base_url=app_settings.llm_base_url)
        except llm.LLMUnavailableError as exc:
            raise ValidationError(str(exc)) from exc

    async def get_llm_model_status(self, model: str) -> LLMModelStatus:
        app_settings = await self.settings_repository.get()
        key = (app_settings.llm_base_url, model)
        if key in _pulling:
            return LLMModelStatus(model=model, present=False, pulling=True)
        present = await llm.is_model_present(model, base_url=app_settings.llm_base_url)
        return LLMModelStatus(model=model, present=present, pulling=False)

    async def trigger_model_pull(self, model: str) -> None:
        """Kick off a model pull in the background, by name, for use by
        any agent — never awaited by the request that calls this, since a
        pull can take minutes. Progress is observed via
        `get_llm_model_status`, mirroring
        `app.features.settings.service.SettingsService.trigger_model_pull`."""
        app_settings = await self.settings_repository.get()
        base_url = app_settings.llm_base_url
        key = (base_url, model)
        if key in _pulling:
            return
        _pulling.add(key)

        async def _run() -> None:
            try:
                if not await llm.is_model_present(model, base_url=base_url):
                    await llm.pull_model(model, base_url=base_url)
            except Exception:
                logger.exception("Background pull of Ollama model %r failed", model)
            finally:
                _pulling.discard(key)

        asyncio.create_task(_run())  # noqa: RUF006 - intentionally fire-and-forget


def _format_agent_report(agent: DataAgent, run: AgentRun) -> str:
    ok = run.status == AgentRunStatus.SUCCESS
    if ok:
        body = (
            f"Considered {run.rows_considered}, selected {run.rows_selected}, "
            f"wrote {run.rows_written} records."
        )
    else:
        body = f"Failed: {run.error_message or 'unknown error'}"
    return f"{'✅' if ok else '❌'} <b>Agent: {agent.name}</b>\n{body}"
