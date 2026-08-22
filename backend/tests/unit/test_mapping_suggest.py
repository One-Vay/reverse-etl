"""Unit tests for the AI mapping-suggestion service, with the Ollama
client mocked — never talks to a real LLM."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from app.core.llm import LLMUnavailableError
from app.features.mappings.schemas import SuggestFieldInfo
from app.features.mappings.suggest import suggest_mappings
from app.features.settings.schemas import AppSettingsRead


def make_settings(**overrides) -> AppSettingsRead:
    defaults = {
        "scheduler_enabled": True,
        "scheduler_poll_interval_seconds": 30,
        "llm_enabled": True,
        "llm_base_url": "http://ollama:11434",
        "llm_model": "qwen2.5:0.5b",
        "telegram_enabled": False,
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "default_connect_timeout_seconds": 10.0,
        "default_request_timeout_seconds": 30.0,
        "updated_at": datetime.now(),
    }
    defaults.update(overrides)
    return AppSettingsRead(**defaults)


SOURCE_COLUMNS = [
    SuggestFieldInfo(name="full_name", data_type="text"),
    SuggestFieldInfo(name="email", data_type="text"),
    SuggestFieldInfo(name="internal_notes", data_type="text"),
]
DESTINATION_FIELDS = [
    SuggestFieldInfo(name="TITLE", data_type="string"),
    SuggestFieldInfo(name="EMAIL", data_type="crm_multifield"),
]


class TestSuggestMappings:
    @pytest.mark.asyncio
    async def test_returns_empty_with_a_message_when_llm_disabled(self):
        result = await suggest_mappings(
            SOURCE_COLUMNS,
            DESTINATION_FIELDS,
            settings=make_settings(llm_enabled=False),
        )

        assert result.pairs == []
        assert result.message is not None

    @pytest.mark.asyncio
    async def test_returns_valid_pairs_from_the_model(self):
        llm_response = {
            "pairs": [
                {
                    "source_field": "full_name",
                    "destination_field": "TITLE",
                    "confidence": 0.9,
                },
                {
                    "source_field": "email",
                    "destination_field": "EMAIL",
                    "confidence": 0.95,
                },
            ]
        }
        with patch(
            "app.features.mappings.suggest.llm.generate_json",
            AsyncMock(return_value=llm_response),
        ):
            result = await suggest_mappings(
                SOURCE_COLUMNS, DESTINATION_FIELDS, settings=make_settings()
            )

        assert len(result.pairs) == 2
        assert result.pairs[0].source_field == "full_name"
        assert result.pairs[0].destination_field == "TITLE"

    @pytest.mark.asyncio
    async def test_drops_hallucinated_field_names(self):
        llm_response = {
            "pairs": [
                {
                    "source_field": "full_name",
                    "destination_field": "TITLE",
                    "confidence": 0.9,
                },
                {
                    "source_field": "made_up_column",
                    "destination_field": "TITLE",
                    "confidence": 0.5,
                },
                {
                    "source_field": "email",
                    "destination_field": "MADE_UP_FIELD",
                    "confidence": 0.5,
                },
            ]
        }
        with patch(
            "app.features.mappings.suggest.llm.generate_json",
            AsyncMock(return_value=llm_response),
        ):
            result = await suggest_mappings(
                SOURCE_COLUMNS, DESTINATION_FIELDS, settings=make_settings()
            )

        assert len(result.pairs) == 1
        assert result.pairs[0].source_field == "full_name"

    @pytest.mark.asyncio
    async def test_drops_duplicate_destination_field_reuse(self):
        llm_response = {
            "pairs": [
                {
                    "source_field": "full_name",
                    "destination_field": "TITLE",
                    "confidence": 0.9,
                },
                {
                    "source_field": "email",
                    "destination_field": "TITLE",
                    "confidence": 0.5,
                },
            ]
        }
        with patch(
            "app.features.mappings.suggest.llm.generate_json",
            AsyncMock(return_value=llm_response),
        ):
            result = await suggest_mappings(
                SOURCE_COLUMNS, DESTINATION_FIELDS, settings=make_settings()
            )

        assert len(result.pairs) == 1

    @pytest.mark.asyncio
    async def test_llm_unavailable_returns_empty_with_message_not_an_error(self):
        with patch(
            "app.features.mappings.suggest.llm.generate_json",
            AsyncMock(side_effect=LLMUnavailableError("connection refused")),
        ):
            result = await suggest_mappings(
                SOURCE_COLUMNS, DESTINATION_FIELDS, settings=make_settings()
            )

        assert result.pairs == []
        assert "connection refused" in result.message

    @pytest.mark.asyncio
    async def test_malformed_top_level_response_returns_no_pairs(self):
        with patch(
            "app.features.mappings.suggest.llm.generate_json",
            AsyncMock(return_value=["not", "a", "dict"]),
        ):
            result = await suggest_mappings(
                SOURCE_COLUMNS, DESTINATION_FIELDS, settings=make_settings()
            )

        assert result.pairs == []

    @pytest.mark.asyncio
    async def test_clamps_out_of_range_confidence(self):
        llm_response = {
            "pairs": [
                {
                    "source_field": "full_name",
                    "destination_field": "TITLE",
                    "confidence": 5.0,
                }
            ]
        }
        with patch(
            "app.features.mappings.suggest.llm.generate_json",
            AsyncMock(return_value=llm_response),
        ):
            result = await suggest_mappings(
                SOURCE_COLUMNS, DESTINATION_FIELDS, settings=make_settings()
            )

        assert result.pairs[0].confidence == 1.0
