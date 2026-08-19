"""AI-suggested field mappings: given a source table's columns and a
destination entity's fields, ask the configured local LLM (see
`app.core.llm`) to propose which pairs are the best semantic match, for
`MappingBoard` to pre-fill on the frontend.

Never raises for a disabled/unreachable LLM or a malformed response —
returns an empty `pairs` list with an explanatory `message` instead, so
this optional feature can never block the existing manual mapping flow.
"""

from __future__ import annotations

import json
from typing import Any

from app.core import llm
from app.features.mappings.schemas import (
    SuggestedFieldPair,
    SuggestFieldInfo,
    SuggestMappingsResponse,
)
from app.features.settings.schemas import AppSettingsRead


def _build_prompt(
    source_columns: list[SuggestFieldInfo], destination_fields: list[SuggestFieldInfo]
) -> str:
    source_lines = "\n".join(f"- {c.name} ({c.data_type})" for c in source_columns)
    dest_lines = "\n".join(f"- {f.name} ({f.data_type})" for f in destination_fields)
    return (
        "You are matching database columns to CRM fields for a data sync.\n\n"
        f"Source columns:\n{source_lines}\n\n"
        f"Destination fields:\n{dest_lines}\n\n"
        "For each source column that has a clear semantic match among the "
        "destination fields (e.g. a column named 'email' matches a field "
        "named 'EMAIL' or 'Email Address'), propose a pairing. Skip source "
        "columns with no good match rather than guessing. Each destination "
        "field should be used at most once.\n\n"
        'Respond with JSON only, in exactly this shape: {"pairs": '
        '[{"source_field": "<source column name>", '
        '"destination_field": "<destination field name>", '
        '"confidence": <0.0-1.0>}]}'
    )


async def suggest_mappings(
    source_columns: list[SuggestFieldInfo],
    destination_fields: list[SuggestFieldInfo],
    *,
    settings: AppSettingsRead,
) -> SuggestMappingsResponse:
    if not settings.llm_enabled:
        return SuggestMappingsResponse(
            pairs=[],
            message="AI mapping suggestions are disabled — enable them in Settings.",
        )

    prompt = _build_prompt(source_columns, destination_fields)
    try:
        result = await llm.generate_json(
            prompt, model=settings.llm_model, base_url=settings.llm_base_url
        )
    except llm.LLMUnavailableError as exc:
        return SuggestMappingsResponse(pairs=[], message=str(exc))

    return SuggestMappingsResponse(
        pairs=_validate_pairs(result, source_columns, destination_fields)
    )


def _validate_pairs(
    result: Any,
    source_columns: list[SuggestFieldInfo],
    destination_fields: list[SuggestFieldInfo],
) -> list[SuggestedFieldPair]:
    """Keep only pairs that reference real field names on both sides, so a
    hallucinated field name can't slip through into the UI. Also enforces
    "each destination field used at most once", in case the model ignores
    that part of the prompt."""
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            return []
    if not isinstance(result, dict):
        return []

    valid_sources = {c.name for c in source_columns}
    valid_destinations = {f.name for f in destination_fields}
    used_destinations: set[str] = set()
    pairs: list[SuggestedFieldPair] = []

    for item in result.get("pairs", []):
        if not isinstance(item, dict):
            continue
        source_field = item.get("source_field")
        destination_field = item.get("destination_field")
        if (
            source_field not in valid_sources
            or destination_field not in valid_destinations
        ):
            continue
        if destination_field in used_destinations:
            continue
        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        used_destinations.add(destination_field)
        pairs.append(
            SuggestedFieldPair(
                source_field=source_field,
                destination_field=destination_field,
                confidence=confidence,
            )
        )

    return pairs
