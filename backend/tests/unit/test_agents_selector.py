"""Unit tests for LLM-driven row selection, with the LLM client mocked."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import ValidationError
from app.features.agents.models import SelectionStrategy
from app.features.agents.selector import score_rows


async def _score(rows, results, **overrides):
    kwargs = {
        "goal": "Increase conversion",
        "actions": "Direct calls",
        "selection_rule": "Score by purchase likelihood",
        "strategy": SelectionStrategy.SCORING,
        "feature_notes": [],
        "model": "qwen2.5:0.5b",
        "base_url": "http://ollama:11434",
        **overrides,
    }
    with patch(
        "app.features.agents.selector.llm.generate_json",
        AsyncMock(side_effect=results if isinstance(results, list) else [results]),
    ):
        return await score_rows(rows, **kwargs)


class TestScoreRows:
    @pytest.mark.asyncio
    async def test_returns_a_score_per_row(self):
        rows = [{"id": 1}, {"id": 2}]
        result = {
            "scores": [
                {"index": 0, "score": 0.9, "reason": "recent buyer"},
                {"index": 1, "score": 0.1, "reason": "no activity"},
            ]
        }
        scores = await _score(rows, result)
        assert [s.index for s in scores] == [0, 1]
        assert scores[0].score == 0.9
        assert scores[0].reason == "recent buyer"
        assert scores[1].score == 0.1

    @pytest.mark.asyncio
    async def test_clamps_out_of_range_scores(self):
        rows = [{"id": 1}]
        result = {"scores": [{"index": 0, "score": 5.0, "reason": "x"}]}
        scores = await _score(rows, result)
        assert scores[0].score == 1.0

    @pytest.mark.asyncio
    async def test_a_row_the_model_skips_is_treated_as_unscored_not_dropped(self):
        rows = [{"id": 1}, {"id": 2}]
        result = {"scores": [{"index": 0, "score": 0.8, "reason": "x"}]}
        scores = await _score(rows, result)
        assert len(scores) == 2
        assert scores[1].score == 0.0

    @pytest.mark.asyncio
    async def test_malformed_response_yields_all_unscored_rows(self):
        rows = [{"id": 1}, {"id": 2}]
        scores = await _score(rows, "not json")
        assert len(scores) == 2
        assert all(s.score == 0.0 for s in scores)

    @pytest.mark.asyncio
    async def test_batches_large_row_sets(self):
        rows = [{"id": i} for i in range(25)]
        batch1 = {
            "scores": [{"index": i, "score": 1.0, "reason": "x"} for i in range(15)]
        }
        batch2 = {
            "scores": [{"index": i, "score": 1.0, "reason": "x"} for i in range(10)]
        }
        with patch(
            "app.features.agents.selector.llm.generate_json",
            AsyncMock(side_effect=[batch1, batch2]),
        ) as mock_generate:
            scores = await score_rows(
                rows,
                goal="g",
                actions="a",
                selection_rule="r",
                strategy=SelectionStrategy.SCORING,
                feature_notes=[],
                model="m",
                base_url="http://x",
                batch_size=15,
            )
        assert mock_generate.await_count == 2
        assert len(scores) == 25
        # Second-batch indices are offset into the full row list.
        assert scores[20].index == 20

    @pytest.mark.asyncio
    async def test_llm_failure_raises_validation_error(self):
        from app.core.llm import LLMUnavailableError

        with patch(
            "app.features.agents.selector.llm.generate_json",
            AsyncMock(side_effect=LLMUnavailableError("down")),
        ):
            with pytest.raises(ValidationError):
                await score_rows(
                    [{"id": 1}],
                    goal="g",
                    actions="a",
                    selection_rule="r",
                    strategy=SelectionStrategy.SCORING,
                    feature_notes=[],
                    model="m",
                    base_url="http://x",
                )

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_rows(self):
        scores = await score_rows(
            [],
            goal="g",
            actions="a",
            selection_rule="r",
            strategy=SelectionStrategy.SCORING,
            feature_notes=[],
            model="m",
            base_url="http://x",
        )
        assert scores == []
