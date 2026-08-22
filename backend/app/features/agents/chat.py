"""Conversational help for one data agent: lets a user ask questions
("why was this row selected?", "why do my leads show no name?") or ask
for troubleshooting help, with the agent's own goal/plan/mapping/last run
as context — so the answers are grounded in what's actually configured,
not generic advice.

Deliberately read-only: the assistant answers in the thread, it never
changes the agent's configuration itself. A person reviews any suggested
fix and applies it through the normal form — keeping "what will happen"
fully visible rather than letting a chat message silently mutate things.
"""

from __future__ import annotations

import json

from app.core import llm
from app.core.exceptions import ValidationError
from app.features.agents.models import AgentRun, ChatRole, DataAgent
from app.features.mappings.models import Mapping

# How many prior turns to include for context — enough for a coherent
# back-and-forth without the prompt growing unbounded over a long thread.
_HISTORY_TURNS = 12


def _build_prompt(
    agent: DataAgent,
    mapping: Mapping,
    last_run: AgentRun | None,
    history: list[tuple[ChatRole, str]],
    message: str,
) -> str:
    plan = agent.plan or {}
    field_mappings = json.dumps(mapping.field_mappings, ensure_ascii=False)

    context_lines = [
        f"Agent name: {agent.name}",
        f"Goal: {agent.goal}",
        f"Planned actions: {agent.actions}",
        f"Source table: {mapping.source_table}",
        f"Destination entity: {mapping.destination_entity}",
        f"Field mappings (source_field -> destination_field): {field_mappings}",
        f"Selection strategy: {agent.selection_strategy}",
        f"Selection threshold: {agent.selection_threshold}",
        f"Annotation field (receives the score/reason on each record): "
        f"{agent.annotation_field or '(none set)'}",
    ]
    if plan:
        context_lines.append(
            f"Current plan's selection rule: {plan.get('selection_rule')}"
        )
        context_lines.append(f"Current plan's reasoning: {plan.get('reasoning')}")
    if last_run:
        context_lines.append(
            "Last run: "
            f"status={last_run.status}, "
            f"considered={last_run.rows_considered}, "
            f"selected={last_run.rows_selected}, "
            f"written={last_run.rows_written}"
            + (f", error={last_run.error_message}" if last_run.error_message else "")
        )
        if last_run.selection_summary:
            context_lines.append(f"Last run's summary: {last_run.selection_summary}")

    history_lines = [
        f"{'User' if role == ChatRole.USER else 'Assistant'}: {content}"
        for role, content in history
    ]

    return (
        "You are a helpful assistant embedded in a reverse-ETL console, "
        "helping a user operate one specific data agent that selects rows "
        "from a database table and loads them into a CRM. Answer clearly "
        "and practically, grounded in the configuration below — don't "
        "give generic advice that ignores it. You cannot change the "
        "agent's configuration yourself: if a fix is needed (e.g. mapping "
        "a name field, changing the threshold, adjusting the goal text), "
        "tell the user exactly what to change and where in the console to "
        "change it, rather than claiming you did it.\n\n"
        "Current configuration:\n"
        + "\n".join(context_lines)
        + "\n\n"
        + (
            "Conversation so far:\n" + "\n".join(history_lines) + "\n\n"
            if history_lines
            else ""
        )
        + f"User: {message}\n\nAssistant:"
    )


async def reply(
    agent: DataAgent,
    mapping: Mapping,
    last_run: AgentRun | None,
    history: list[tuple[ChatRole, str]],
    message: str,
    *,
    base_url: str,
) -> str:
    """Ask the agent's configured LLM to respond to `message`, given the
    agent's configuration and recent chat history as context.

    Raises:
        ValidationError: If the LLM is unreachable or returns nothing.
    """
    prompt = _build_prompt(agent, mapping, last_run, history[-_HISTORY_TURNS:], message)
    try:
        text = await llm.generate_text(
            prompt, model=agent.llm_model, base_url=base_url, timeout=120.0
        )
    except llm.LLMUnavailableError as exc:
        raise ValidationError(f"Couldn't reach the agent's model: {exc}") from exc

    text = text.strip()
    if not text:
        raise ValidationError("The model returned an empty reply.")
    return text
