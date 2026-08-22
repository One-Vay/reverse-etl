"""Executes one `DataAgent`: fetches newly-arrived rows from its mapping's
source table, scores them against the agent's goal via the local LLM
(see `app.features.agents.selector`), writes only the selected subset to
the destination through the same mapping/connector machinery the sync
engine uses, and records the outcome as an `AgentRun`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import ConnectorError
from app.core.exceptions import ValidationError
from app.features.agents.models import AgentRun, AgentRunStatus, DataAgent
from app.features.agents.repository import AgentRepository, AgentRunRepository
from app.features.agents.schemas import FeatureNote
from app.features.agents.selector import RowScore, score_rows
from app.features.destinations.repository import DestinationRepository
from app.features.destinations.service import DestinationService
from app.features.mappings.transform import transform_row
from app.features.settings.repository import SettingsRepository
from app.features.sources.repository import SourceRepository
from app.features.sources.service import SourceService

# Shown to the user as a max of this many example rows per run, sorted by
# score — not the model's full per-row reasoning, just enough to explain
# what got selected without bloating the AgentRun record.
_SUMMARY_EXAMPLE_COUNT = 5


async def execute(agent: DataAgent, *, session: AsyncSession) -> AgentRun:
    """Run one agent end-to-end and persist the result as an `AgentRun`.

    Never raises for a connector/LLM failure — recorded as a failed
    `AgentRun` instead, mirroring `app.features.syncs.runner.execute`, so
    a broken agent can't crash the request that triggered it.
    """
    started_at = datetime.now(timezone.utc)
    run_repo = AgentRunRepository(session)
    agent_repo = AgentRepository(session)

    rows_considered = 0
    rows_selected = 0
    rows_written = 0
    selection_summary: str | None = None
    error_message: str | None = None

    try:
        mapping = agent.mapping
        app_settings = await SettingsRepository(session).get()
        if not app_settings.llm_enabled:
            raise ValidationError(
                "AI mapping suggestions must be enabled in Settings before "
                "an agent can run — agents use the same local LLM."
            )

        source_service = SourceService(SourceRepository(session))
        source_connector = await source_service.build_connector(mapping.source_id)
        async with source_connector:
            rows = await source_connector.fetch_data(
                mapping.source_table, where=_incremental_where(agent)
            )
        rows_considered = len(rows)

        if rows:
            feature_notes = [FeatureNote(**note) for note in agent.feature_notes]
            plan = agent.plan or {}
            selection_rule = plan.get("selection_rule") or agent.goal
            scores = await score_rows(
                rows,
                goal=agent.goal,
                actions=agent.actions,
                selection_rule=selection_rule,
                strategy=agent.selection_strategy,
                feature_notes=feature_notes,
                model=agent.llm_model,
                base_url=app_settings.llm_base_url,
            )
            selected = [s for s in scores if s.score >= agent.selection_threshold]
            rows_selected = len(selected)
            selection_summary = _summarize(scores, agent.selection_threshold)

            if selected:
                records = [
                    transform_row(rows[s.index], mapping.field_mappings)
                    for s in selected
                ]
                destination_service = DestinationService(DestinationRepository(session))
                destination_connector = await destination_service.build_connector(
                    agent.destination_id
                )
                async with destination_connector:
                    rows_written = await destination_connector.upsert_data(
                        mapping.destination_entity, records
                    )

        status = AgentRunStatus.SUCCESS
    except ConnectorError as exc:
        status = AgentRunStatus.FAILED
        error_message = str(exc)
    except ValidationError as exc:
        status = AgentRunStatus.FAILED
        error_message = str(exc)
    except Exception as exc:  # noqa: BLE001 - a broken agent must not crash the caller
        status = AgentRunStatus.FAILED
        error_message = f"Unexpected error: {exc}"

    finished_at = datetime.now(timezone.utc)
    run = await run_repo.create(
        agent_id=agent.id,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        rows_considered=rows_considered,
        rows_selected=rows_selected,
        rows_written=rows_written,
        selection_summary=selection_summary,
        error_message=error_message,
    )
    await agent_repo.update_last_run(agent.id, finished_at)

    return run


def _incremental_where(agent: DataAgent) -> str | None:
    """A `WHERE` clause that only reads rows newer than the last run, for
    agents with `incremental_field` configured. Falls back to a full-table
    read on the very first run (no `last_run_at` yet) or when incremental
    selection isn't configured — mirrors
    `app.features.syncs.runner._incremental_where`."""
    if not agent.incremental_field or not agent.last_run_at:
        return None
    watermark = agent.last_run_at.isoformat()
    return f"{agent.incremental_field} > '{watermark}'"


def _summarize(scores: list[RowScore], threshold: float) -> str:
    selected = [s for s in scores if s.score >= threshold]
    lines = [
        f"Selected {len(selected)} of {len(scores)} rows considered "
        f"(threshold {threshold:.2f})."
    ]
    top = sorted(selected, key=lambda s: -s.score)[:_SUMMARY_EXAMPLE_COUNT]
    for s in top:
        if s.reason:
            lines.append(f"- row {s.index} (score {s.score:.2f}): {s.reason}")
    return "\n".join(lines)
