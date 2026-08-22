"""Executes one `DataAgent`: fetches newly-arrived rows from its mapping's
source table, scores them against the agent's goal via the local LLM
(see `app.features.agents.selector`), writes only the selected subset to
the destination through the same mapping/connector machinery the sync
engine uses, and records the outcome as an `AgentRun`.

`preview()` shares the same fetch/score/annotate path as `execute()` but
never writes — the step between "Generate plan" and "Run now" that lets a
user see exactly which rows would be selected, with what reasoning, and
the actual record that would be sent, before committing to it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

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


@dataclass(frozen=True, slots=True)
class PreparedSelection:
    """The fetch+score+annotate step's result — everything `execute()`
    needs to write, and everything `preview()` needs to show, without
    either duplicating the other's logic."""

    rows_considered: int
    scores: list[RowScore]
    row_details: list[dict[str, Any]]
    records_to_write: list[dict[str, Any]]


async def _prepare(agent: DataAgent, *, session: AsyncSession) -> PreparedSelection:
    """Fetch due rows, score them against the agent's goal, and build the
    annotated records that would be written for the ones above threshold.

    Raises:
        ValidationError: If the LLM isn't enabled in Settings.
        ConnectorError: If the source can't be reached.
    """
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

    if not rows:
        return PreparedSelection(0, [], [], [])

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

    row_details: list[dict[str, Any]] = []
    records_to_write: list[dict[str, Any]] = []
    for s in scores:
        selected = s.score >= agent.selection_threshold
        detail: dict[str, Any] = {
            "index": s.index,
            "score": s.score,
            "reason": s.reason,
            "selected": selected,
            "record": None,
        }
        if selected:
            record = transform_row(rows[s.index], mapping.field_mappings)
            _annotate(record, agent=agent, score=s)
            detail["record"] = record
            records_to_write.append(record)
        row_details.append(detail)

    return PreparedSelection(len(rows), scores, row_details, records_to_write)


def _annotate(record: dict[str, Any], *, agent: DataAgent, score: RowScore) -> None:
    """Write the selection score and the model's reason into the
    destination field the agent designates (`annotation_field`), so a
    person looking at the loaded record — not just the console — can see
    why it was chosen and what to do with it. A no-op unless the agent
    configures a field for this."""
    if not agent.annotation_field:
        return
    note = f'Selected by agent "{agent.name}" — score {score.score:.2f}.'
    if score.reason:
        note += f" {score.reason}"
    record[agent.annotation_field] = note


async def preview(agent: DataAgent, *, session: AsyncSession) -> PreparedSelection:
    """Dry-run an agent: score its due rows and build what would be
    written, without touching the destination or persisting a run. Lets
    the console show a concrete "here's what will happen" step before the
    user commits to `execute()`.

    Raises the same errors as `execute()` — callers should let them
    propagate as an HTTP error, unlike `execute()` which records them on
    the `AgentRun` instead, since there's no run to record here.
    """
    return await _prepare(agent, session=session)


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
    row_details: list[dict[str, Any]] = []
    error_message: str | None = None

    try:
        prepared = await _prepare(agent, session=session)
        rows_considered = prepared.rows_considered
        rows_selected = len(prepared.records_to_write)
        row_details = prepared.row_details
        selection_summary = _summarize(prepared.scores, agent.selection_threshold)

        if prepared.records_to_write:
            mapping = agent.mapping
            destination_service = DestinationService(DestinationRepository(session))
            destination_connector = await destination_service.build_connector(
                agent.destination_id
            )
            async with destination_connector:
                rows_written = await destination_connector.upsert_data(
                    mapping.destination_entity, prepared.records_to_write
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
        row_details=row_details,
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
