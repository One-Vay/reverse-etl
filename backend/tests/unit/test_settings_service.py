"""Unit tests for SettingsRepository/SettingsService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.settings.repository import SettingsRepository
from app.features.settings.schemas import AppSettingsUpdate
from app.features.settings.service import SettingsService, _pulling


def make_settings_row(**overrides):
    row = MagicMock()
    row.scheduler_enabled = overrides.get("scheduler_enabled", True)
    row.scheduler_poll_interval_seconds = overrides.get(
        "scheduler_poll_interval_seconds", 30
    )
    row.llm_enabled = overrides.get("llm_enabled", False)
    row.llm_base_url = overrides.get("llm_base_url", "http://ollama:11434")
    row.llm_model = overrides.get("llm_model", "qwen2.5:0.5b")
    row.default_connect_timeout_seconds = overrides.get(
        "default_connect_timeout_seconds", 10.0
    )
    row.default_request_timeout_seconds = overrides.get(
        "default_request_timeout_seconds", 30.0
    )
    from datetime import datetime

    row.updated_at = overrides.get("updated_at", datetime.now())
    return row


class TestSettingsRepositoryGetOrCreate:
    @pytest.mark.asyncio
    async def test_creates_the_row_on_first_access(self):
        session = MagicMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        repo = SettingsRepository(session)

        await repo.get()

        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_returns_the_existing_row_without_creating_again(self):
        existing = make_settings_row()
        session = MagicMock()
        session.add = MagicMock()
        session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing))
        )
        repo = SettingsRepository(session)

        result = await repo.get()

        assert result is existing
        session.add.assert_not_called()


class TestSettingsService:
    @pytest.mark.asyncio
    async def test_get_returns_the_repository_row(self):
        repo = MagicMock()
        repo.get = AsyncMock(return_value=make_settings_row())
        service = SettingsService(repo)

        result = await service.get()

        assert result.scheduler_poll_interval_seconds == 30

    @pytest.mark.asyncio
    async def test_update_triggers_a_pull_when_llm_is_enabled(self):
        repo = MagicMock()
        repo.update = AsyncMock(return_value=make_settings_row(llm_enabled=True))
        service = SettingsService(repo)

        with patch.object(service, "trigger_model_pull") as mock_trigger:
            await service.update(AppSettingsUpdate(llm_enabled=True))

        mock_trigger.assert_called_once_with("http://ollama:11434", "qwen2.5:0.5b")

    @pytest.mark.asyncio
    async def test_update_does_not_pull_when_llm_flag_is_untouched(self):
        repo = MagicMock()
        repo.update = AsyncMock(return_value=make_settings_row())
        service = SettingsService(repo)

        with patch.object(service, "trigger_model_pull") as mock_trigger:
            await service.update(AppSettingsUpdate(scheduler_enabled=False))

        mock_trigger.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_status_reports_pulling_without_a_network_call(self):
        repo = MagicMock()
        repo.get = AsyncMock(
            return_value=make_settings_row(llm_base_url="http://x:11434", llm_model="m")
        )
        service = SettingsService(repo)
        _pulling.add(("http://x:11434", "m"))
        try:
            with patch(
                "app.features.settings.service.llm.is_model_present",
                AsyncMock(side_effect=AssertionError("should not be called")),
            ):
                status = await service.get_llm_status()
        finally:
            _pulling.discard(("http://x:11434", "m"))

        assert status.pulling is True
        assert status.model_present is False

    @pytest.mark.asyncio
    async def test_llm_status_checks_ollama_when_not_pulling(self):
        repo = MagicMock()
        repo.get = AsyncMock(return_value=make_settings_row())
        service = SettingsService(repo)

        with patch(
            "app.features.settings.service.llm.is_model_present",
            AsyncMock(return_value=True),
        ):
            status = await service.get_llm_status()

        assert status.model_present is True
        assert status.pulling is False
