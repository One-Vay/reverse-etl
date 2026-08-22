"""Row selection: given a batch of newly-arrived source rows, ask the
configured local LLM to judge each one against the agent's goal and its
plan's selection rule, so only the relevant subset gets loaded into the
destination — not the whole table.

Every `SelectionStrategy` (see `app.features.agents.models`) goes through
this same function; the strategy only changes how the prompt frames the
judgment (a probability estimate, a cluster-membership check, or explicit
rule matching), not the {score, reason} JSON shape returned per row.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.core import llm
from app.core.exceptions import ValidationError
from app.features.agents.models import SelectionStrategy
from app.features.agents.schemas import FeatureNote

logger = logging.getLogger(__name__)

# Batched rather than one LLM call per row — keeps the number of Ollama
# round-trips manageable for a table with hundreds of new rows, while
# staying small enough that a small local model can reliably reason
# about every row in the batch instead of skimming a huge prompt.
_BATCH_SIZE = 15

_STRATEGY_FRAMING = {
    SelectionStrategy.SCORING: (
        "Score how likely each row is to match the goal (e.g. probability "
        "of converting, purchasing, or otherwise responding to the "
        "planned actions), from 0.0 (no chance) to 1.0 (certain match)."
    ),
    SelectionStrategy.CLUSTERING: (
        "Judge which rows belong to the segment described by the goal, as "
        "if grouping all rows into clusters and keeping only the cluster "
        "that matches. Score 1.0 for a clear match to that segment, 0.0 "
        "for a clear non-match, and something in between for an ambiguous "
        "case."
    ),
    SelectionStrategy.RULE_BASED: (
        "Apply the selection rule as an explicit, literal criterion. Score "
        "1.0 if the row satisfies the rule, 0.0 if it doesn't — avoid "
        "partial scores unless the rule is genuinely a matter of degree."
    ),
}


@dataclass(frozen=True, slots=True)
class RowScore:
    """One row's selection judgment.

    Attributes:
        index: The row's position in the full list passed to
            `score_rows` (not just within its batch).
        score: 0.0-1.0, meaning depends on `SelectionStrategy` — see
            `_STRATEGY_FRAMING`.
        reason: The model's one-line explanation, shown to the user.
    """

    index: int
    score: float
    reason: str


def _build_batch_prompt(
    batch: list[dict[str, Any]],
    *,
    goal: str,
    actions: str,
    selection_rule: str,
    strategy: SelectionStrategy,
    feature_notes: list[FeatureNote],
) -> str:
    notes_text = (
        "\n".join(f"- {note.column}: {note.description}" for note in feature_notes)
        if feature_notes
        else "(none provided)"
    )
    rows_text = json.dumps(
        [{"index": i, "row": row} for i, row in enumerate(batch)],
        default=str,
        ensure_ascii=False,
    )
    return (
        "You are selecting which rows of a database table are worth "
        "loading into a CRM for a specific business goal — not every row, "
        "only the ones that matter for this goal.\n\n"
        f"Goal: {goal}\n\n"
        f"Planned actions on selected rows: {actions}\n\n"
        f"Selection rule from the agreed plan: {selection_rule}\n\n"
        f"Notes on specific columns:\n{notes_text}\n\n"
        f"{_STRATEGY_FRAMING[strategy]}\n\n"
        f"Rows to judge (JSON array, each with its index):\n{rows_text}\n\n"
        "Judge every row in the array — don't skip any. Respond with JSON "
        'only, in exactly this shape: {"scores": [{"index": <the row\'s '
        'index from above>, "score": <0.0-1.0>, "reason": "<brief, '
        'one-sentence reason>"}]}'
    )


async def score_rows(
    rows: list[dict[str, Any]],
    *,
    goal: str,
    actions: str,
    selection_rule: str,
    strategy: SelectionStrategy,
    feature_notes: list[FeatureNote],
    model: str,
    base_url: str,
    batch_size: int = _BATCH_SIZE,
) -> list[RowScore]:
    """Score every row in `rows` against the agent's goal, in batches.

    Raises:
        ValidationError: If the LLM is unreachable or never returns a
            usable score for a given batch — a failed judgment must not
            silently drop rows from consideration, so this surfaces as an
            error the caller turns into a failed `AgentRun` rather than a
            quietly-incomplete selection.
    """
    scores: list[RowScore] = []
    for offset in range(0, len(rows), batch_size):
        batch = rows[offset : offset + batch_size]
        prompt = _build_batch_prompt(
            batch,
            goal=goal,
            actions=actions,
            selection_rule=selection_rule,
            strategy=strategy,
            feature_notes=feature_notes,
        )
        try:
            result = await llm.generate_json(
                prompt, model=model, base_url=base_url, timeout=180.0
            )
        except llm.LLMUnavailableError as exc:
            raise ValidationError(f"Row selection failed: {exc}") from exc

        scores.extend(_parse_batch(result, batch_len=len(batch), offset=offset))

    return scores


def _parse_batch(result: Any, *, batch_len: int, offset: int) -> list[RowScore]:
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            result = {}
    if not isinstance(result, dict):
        result = {}

    by_index: dict[int, RowScore] = {}
    for item in result.get("scores", []) if isinstance(result, dict) else []:
        if not isinstance(item, dict):
            continue
        raw_index = item.get("index")
        if raw_index is None:
            continue
        try:
            local_index = int(raw_index)
            score = float(item.get("score", 0.0))
        except (TypeError, ValueError):
            continue
        if not 0 <= local_index < batch_len:
            continue
        score = max(0.0, min(1.0, score))
        reason = str(item.get("reason") or "").strip()
        by_index[local_index] = RowScore(
            index=offset + local_index, score=score, reason=reason
        )

    # A row the model skipped is treated as unscored (0.0, no reason)
    # rather than dropped — every input row must produce an output row so
    # counts stay consistent for the caller (rows_considered vs. scores
    # returned), and a skipped row shouldn't accidentally end up selected.
    missing = set(range(batch_len)) - set(by_index)
    if missing:
        logger.warning(
            "LLM skipped %d of %d rows in a selection batch — treating as unscored",
            len(missing),
            batch_len,
        )
    for local_index in missing:
        by_index[local_index] = RowScore(
            index=offset + local_index, score=0.0, reason="(not scored by the model)"
        )

    return [by_index[i] for i in sorted(by_index)]
