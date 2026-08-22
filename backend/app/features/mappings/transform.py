"""Applies a field mapping's `transformation` preset to a raw source value.

The preset names are defined once, client-side, in
`frontend/src/lib/transformations.ts` — that file's own docstring says
"the sync engine (not built yet) interprets these names when it applies a
mapping". This module is that engine-side half of the contract, so the
set of names handled here must stay in sync with that file.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Presets that don't need a value transform: "" is the frontend's "None"
# option, and unset covers columns not typed at all.
_PASSTHROUGH = {"", None}

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d.%m.%Y",
    "%d/%m/%Y",
)


def apply_transformation(value: Any, transformation: str | None) -> Any:
    """Apply a named preset transformation to a single field value.

    Args:
        value: The raw value read from the source row. `None` passes
            through unchanged regardless of preset — there's nothing a
            string-oriented preset can meaningfully do to a null.
        transformation: One of the preset names from
            `TRANSFORMATION_PRESETS` in `frontend/src/lib/transformations.ts`,
            `""`/`None` for no-op, or free-form text a user typed in the
            "Custom…" preset (also treated as a no-op — arbitrary
            expression evaluation is out of scope; see that file's
            `CUSTOM_TRANSFORMATION` sentinel).

    Returns:
        The transformed value, or `value` unchanged if there's no matching
        preset or `value` is `None`.
    """
    if value is None or transformation in _PASSTHROUGH:
        return value

    if transformation == "lowercase":
        return str(value).lower()
    if transformation == "uppercase":
        return str(value).upper()
    if transformation == "trim":
        return str(value).strip()
    if transformation == "to_string":
        return str(value)
    if transformation == "to_number":
        return _to_number(value)
    if transformation == "parse_date":
        return _parse_date(value)

    # Free-form "Custom…" text, or an unrecognized preset — passed through
    # unchanged rather than raising, so a typo in a saved mapping degrades
    # to a no-op instead of failing every sync run.
    return value


def transform_row(
    row: dict[str, Any], field_mappings: list[dict[str, Any]]
) -> dict[str, Any]:
    """Apply every field mapping's transformation to one source row,
    producing the destination-shaped record to write. Shared by the sync
    engine (`app.features.syncs.runner`) and the data-agent engine
    (`app.features.agents.runner`) — both write through the same kind of
    mapping, just selecting a different subset of rows first."""
    record: dict[str, Any] = {}
    for field_mapping in field_mappings:
        source_field = field_mapping["source_field"]
        if source_field not in row:
            continue
        record[field_mapping["destination_field"]] = apply_transformation(
            row[source_field], field_mapping.get("transformation")
        )
    return record


def _to_number(value: Any) -> Any:
    text = str(value).strip()
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return value


def _parse_date(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    return value
