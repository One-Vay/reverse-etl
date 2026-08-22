"""Plan generation: given an agent's goal, planned actions, and the shape
of its source data, ask the configured local LLM to propose a concrete
plan — which selection strategy fits, a plain-language description of
the selection rule it will apply, and recommended next actions.

Deliberately asks for unrestricted reasoning: since this runs against a
local Ollama model rather than a hosted API, there's no reason to cap or
sanitize the model's analysis before showing it to the user — the
`reasoning` field is free text of whatever length the model produces.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.connectors.base import ColumnSchema
from app.core import llm
from app.core.exceptions import ValidationError
from app.features.agents.models import SelectionStrategy
from app.features.agents.schemas import AgentPlan, FeatureNote

logger = logging.getLogger(__name__)

# Keep the sample small — it's only there to ground the plan in what the
# data actually looks like, not to hand the model the whole table.
_SAMPLE_ROW_LIMIT = 5


def _build_prompt(
    *,
    goal: str,
    actions: str,
    table_name: str,
    columns: list[ColumnSchema],
    feature_notes: list[FeatureNote],
    sample_rows: list[dict[str, Any]],
) -> str:
    notes_by_column = {note.column: note.description for note in feature_notes}
    column_lines = "\n".join(
        f"- {c.name} ({c.data_type})"
        + (f" — {notes_by_column[c.name]}" if c.name in notes_by_column else "")
        for c in columns
    )
    sample_text = (
        json.dumps(sample_rows, default=str, ensure_ascii=False)
        if sample_rows
        else "(no sample rows available)"
    )
    strategies = ", ".join(f'"{s.value}"' for s in SelectionStrategy)

    return (
        "You are a data analyst planning a targeted CRM data-loading task. "
        "A user wants to load only the most relevant rows from a database "
        "table into their CRM, not the whole table, and has described their "
        "goal and how they plan to act on the loaded records.\n\n"
        f"Goal: {goal}\n\n"
        f"Planned actions on the loaded records: {actions}\n\n"
        f"Source table: {table_name}\n"
        f"Columns:\n{column_lines}\n\n"
        f"Sample rows (for context, not the full dataset):\n{sample_text}\n\n"
        "Think through this as thoroughly as you want — there's no length "
        "limit on your reasoning, and no topic is off-limits for a "
        "legitimate business analysis. Consider what makes a row a good "
        "candidate for this goal, what risks or caveats the user should "
        "know about (data quality, sample size, potential bias in the "
        f"selection), and which of these strategies fits best: {strategies}. "
        '"scoring" assigns each row a 0-1 probability/relevance score '
        'against a threshold (e.g. purchase likelihood). "clustering" '
        "groups rows and keeps whichever cluster matches the goal. "
        '"rule_based" applies explicit criteria described in the goal '
        "or actions text directly, without a learned score.\n\n"
        "Respond with JSON only, in exactly this shape:\n"
        '{"strategy": "<one of the strategies above>", '
        '"reasoning": "<your full analysis, as long as you need>", '
        '"selection_rule": "<a precise, plain-language description of '
        "exactly how a row will be judged — this is shown to the user and "
        'used to prompt the row-scoring step, so be specific>", '
        '"recommended_threshold": <0.0-1.0 or null if not using scoring>, '
        '"next_actions": ["<concrete next step the user should take, '
        'e.g. specific to their planned actions>", ...]}'
    )


async def generate_plan(
    *,
    goal: str,
    actions: str,
    table_name: str,
    columns: list[ColumnSchema],
    feature_notes: list[FeatureNote],
    sample_rows: list[dict[str, Any]],
    model: str,
    base_url: str,
) -> AgentPlan:
    """Ask the LLM for a plan and return it validated.

    Raises:
        ValidationError: If the LLM is unreachable, the model isn't
            pulled, or the response can't be parsed into a usable plan —
            unlike AI mapping suggestions, a plan is the entire point of
            this endpoint, so there's no silent "degrade to nothing" here.
    """
    prompt = _build_prompt(
        goal=goal,
        actions=actions,
        table_name=table_name,
        columns=columns,
        feature_notes=feature_notes,
        sample_rows=sample_rows,
    )
    try:
        result = await llm.generate_json(
            prompt, model=model, base_url=base_url, timeout=180.0
        )
    except llm.LLMUnavailableError as exc:
        raise ValidationError(f"Couldn't generate a plan: {exc}") from exc

    return _parse_plan(result, model=model)


def _parse_plan(result: Any, *, model: str) -> AgentPlan:
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError as exc:
            raise ValidationError(
                "The model's response wasn't valid JSON — try again, or "
                "try a different model."
            ) from exc
    if not isinstance(result, dict):
        raise ValidationError("The model's response wasn't a JSON object.")

    try:
        strategy = SelectionStrategy(result.get("strategy"))
    except ValueError:
        # A model that ignores the requested shape shouldn't block the
        # whole plan — scoring is the safest, most broadly applicable
        # default when the strategy itself couldn't be parsed.
        logger.warning(
            "Agent plan had an unrecognized strategy %r, defaulting to scoring",
            result.get("strategy"),
        )
        strategy = SelectionStrategy.SCORING

    reasoning = str(result.get("reasoning") or "").strip()
    selection_rule = str(result.get("selection_rule") or "").strip()
    if not reasoning or not selection_rule:
        raise ValidationError(
            "The model's response was missing reasoning or a selection rule."
        )

    threshold = result.get("recommended_threshold")
    try:
        threshold = float(threshold) if threshold is not None else None
        if threshold is not None:
            threshold = max(0.0, min(1.0, threshold))
    except (TypeError, ValueError):
        threshold = None

    next_actions = result.get("next_actions")
    if not isinstance(next_actions, list):
        next_actions = []
    next_actions = [str(item) for item in next_actions if str(item).strip()]

    return AgentPlan(
        strategy=strategy,
        reasoning=reasoning,
        selection_rule=selection_rule,
        recommended_threshold=threshold,
        next_actions=next_actions,
        model=model,
        generated_at=datetime.now(timezone.utc),
    )
