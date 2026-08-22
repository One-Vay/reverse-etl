"""Unit tests for agent chat, with the LLM client mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ValidationError
from app.features.agents.chat import reply
from app.features.agents.models import ChatRole

# A SQLAlchemy column typed `Mapped[SelectionStrategy]` but stored as plain
# `String` comes back from the DB as a plain `str`, not a `SelectionStrategy`
# instance — mocking it as a real enum member here would hide any code that
# assumes `.value` exists (it doesn't, on a plain string) and only breaks in
# production. Same reasoning applies to `AgentRun.status` below.
_SELECTION_STRATEGY_FROM_DB = "scoring"
_RUN_STATUS_FROM_DB = "success"


def make_agent(**overrides):
    agent = MagicMock()
    agent.name = overrides.get("name", "B2B booster")
    agent.goal = overrides.get("goal", "Increase conversion")
    agent.actions = overrides.get("actions", "Direct calls")
    agent.selection_strategy = overrides.get(
        "selection_strategy", _SELECTION_STRATEGY_FROM_DB
    )
    agent.selection_threshold = overrides.get("selection_threshold", 0.6)
    agent.annotation_field = overrides.get("annotation_field", None)
    agent.plan = overrides.get("plan", None)
    return agent


def make_mapping():
    mapping = MagicMock()
    mapping.source_table = "prospects"
    mapping.destination_entity = "lead"
    mapping.field_mappings = [
        {"source_field": "full_name", "destination_field": "TITLE"}
    ]
    return mapping


class TestReply:
    @pytest.mark.asyncio
    async def test_returns_the_models_text_response(self):
        with patch(
            "app.features.agents.chat.llm.generate_text",
            AsyncMock(return_value="Map full_name to NAME as well."),
        ):
            result = await reply(
                make_agent(),
                make_mapping(),
                None,
                [],
                "Why do leads show no name?",
                base_url="http://ollama:11434",
            )
        assert result == "Map full_name to NAME as well."

    @pytest.mark.asyncio
    async def test_includes_goal_and_mapping_in_the_prompt(self):
        with patch(
            "app.features.agents.chat.llm.generate_text", AsyncMock(return_value="ok")
        ) as mock_generate:
            await reply(
                make_agent(goal="Increase conversion"),
                make_mapping(),
                None,
                [],
                "hello",
                base_url="http://ollama:11434",
            )

        prompt = mock_generate.call_args.args[0]
        assert "Increase conversion" in prompt
        assert "prospects" in prompt
        assert "lead" in prompt

    @pytest.mark.asyncio
    async def test_includes_last_run_summary_when_present(self):
        last_run = MagicMock()
        last_run.status = _RUN_STATUS_FROM_DB
        last_run.rows_considered = 10
        last_run.rows_selected = 3
        last_run.rows_written = 3
        last_run.error_message = None
        last_run.selection_summary = "Selected 3 of 10 rows."

        with patch(
            "app.features.agents.chat.llm.generate_text", AsyncMock(return_value="ok")
        ) as mock_generate:
            await reply(
                make_agent(), make_mapping(), last_run, [], "hello", base_url="http://x"
            )

        prompt = mock_generate.call_args.args[0]
        assert "considered=10" in prompt
        assert "Selected 3 of 10 rows." in prompt

    @pytest.mark.asyncio
    async def test_includes_conversation_history(self):
        history = [
            (ChatRole.USER, "first question"),
            (ChatRole.ASSISTANT, "first answer"),
        ]
        with patch(
            "app.features.agents.chat.llm.generate_text", AsyncMock(return_value="ok")
        ) as mock_generate:
            await reply(
                make_agent(),
                make_mapping(),
                None,
                history,
                "follow-up",
                base_url="http://x",
            )

        prompt = mock_generate.call_args.args[0]
        assert "first question" in prompt
        assert "first answer" in prompt

    @pytest.mark.asyncio
    async def test_llm_failure_raises_validation_error(self):
        from app.core.llm import LLMUnavailableError

        with patch(
            "app.features.agents.chat.llm.generate_text",
            AsyncMock(side_effect=LLMUnavailableError("down")),
        ):
            with pytest.raises(ValidationError):
                await reply(
                    make_agent(), make_mapping(), None, [], "hello", base_url="http://x"
                )

    @pytest.mark.asyncio
    async def test_empty_reply_raises_validation_error(self):
        with patch(
            "app.features.agents.chat.llm.generate_text", AsyncMock(return_value="   ")
        ):
            with pytest.raises(ValidationError):
                await reply(
                    make_agent(), make_mapping(), None, [], "hello", base_url="http://x"
                )
