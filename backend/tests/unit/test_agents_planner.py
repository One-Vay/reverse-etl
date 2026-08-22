"""Unit tests for agent plan generation, with the LLM client mocked."""

from unittest.mock import AsyncMock, patch

import pytest

from app.connectors.base import ColumnSchema
from app.core.exceptions import ValidationError
from app.features.agents.models import SelectionStrategy
from app.features.agents.planner import generate_plan
from app.features.agents.schemas import FeatureNote

COLUMNS = [
    ColumnSchema(name="id", data_type="integer", nullable=False, is_primary_key=True),
    ColumnSchema(name="last_purchase_at", data_type="timestamp", nullable=True),
]


async def _generate(result, **overrides):
    kwargs = {
        "goal": "Increase conversion",
        "actions": "Direct calls",
        "table_name": "customers",
        "columns": COLUMNS,
        "feature_notes": [
            FeatureNote(column="last_purchase_at", description="recency")
        ],
        "sample_rows": [{"id": 1, "last_purchase_at": "2026-01-01"}],
        "model": "qwen2.5:0.5b",
        "base_url": "http://ollama:11434",
        **overrides,
    }
    with patch(
        "app.features.agents.planner.llm.generate_json",
        AsyncMock(return_value=result),
    ):
        return await generate_plan(**kwargs)


class TestGeneratePlan:
    @pytest.mark.asyncio
    async def test_returns_a_validated_plan(self):
        plan = await _generate(
            {
                "strategy": "scoring",
                "reasoning": "Recent purchasers convert best.",
                "selection_rule": "Score rows by recency of last_purchase_at.",
                "recommended_threshold": 0.7,
                "next_actions": ["Call top-scoring customers first"],
            }
        )
        assert plan.strategy == SelectionStrategy.SCORING
        assert plan.reasoning == "Recent purchasers convert best."
        assert plan.recommended_threshold == 0.7
        assert plan.next_actions == ["Call top-scoring customers first"]
        assert plan.model == "qwen2.5:0.5b"

    @pytest.mark.asyncio
    async def test_parses_a_json_string_response(self):
        plan = await _generate(
            '{"strategy": "clustering", "reasoning": "x", "selection_rule": "y"}'
        )
        assert plan.strategy == SelectionStrategy.CLUSTERING

    @pytest.mark.asyncio
    async def test_unrecognized_strategy_falls_back_to_scoring(self):
        plan = await _generate(
            {"strategy": "not-a-real-strategy", "reasoning": "x", "selection_rule": "y"}
        )
        assert plan.strategy == SelectionStrategy.SCORING

    @pytest.mark.asyncio
    async def test_missing_reasoning_raises_validation_error(self):
        with pytest.raises(ValidationError):
            await _generate({"strategy": "scoring", "selection_rule": "y"})

    @pytest.mark.asyncio
    async def test_missing_selection_rule_raises_validation_error(self):
        with pytest.raises(ValidationError):
            await _generate({"strategy": "scoring", "reasoning": "x"})

    @pytest.mark.asyncio
    async def test_malformed_json_string_raises_validation_error(self):
        with pytest.raises(ValidationError):
            await _generate("not json at all")

    @pytest.mark.asyncio
    async def test_non_object_response_raises_validation_error(self):
        with pytest.raises(ValidationError):
            await _generate([1, 2, 3])

    @pytest.mark.asyncio
    async def test_out_of_range_threshold_is_clamped(self):
        plan = await _generate(
            {
                "strategy": "scoring",
                "reasoning": "x",
                "selection_rule": "y",
                "recommended_threshold": 5.0,
            }
        )
        assert plan.recommended_threshold == 1.0

    @pytest.mark.asyncio
    async def test_non_list_next_actions_becomes_empty(self):
        plan = await _generate(
            {
                "strategy": "scoring",
                "reasoning": "x",
                "selection_rule": "y",
                "next_actions": "not a list",
            }
        )
        assert plan.next_actions == []
