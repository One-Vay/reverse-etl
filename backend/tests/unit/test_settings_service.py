"""Unit tests for SettingsService's Telegram test-message method, with the
repository and Telegram client mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.telegram import TelegramError
from app.features.settings.service import SettingsService


def make_settings(**overrides):
    settings = MagicMock()
    settings.telegram_enabled = overrides.get("telegram_enabled", True)
    settings.telegram_bot_token = overrides.get("telegram_bot_token", "token")
    settings.telegram_chat_id = overrides.get("telegram_chat_id", "chat-id")
    return settings


@pytest.fixture
def service():
    repo = MagicMock()
    repo.get = AsyncMock(return_value=make_settings())
    return SettingsService(repo), repo


class TestSendTelegramTestMessage:
    @pytest.mark.asyncio
    async def test_sends_a_test_message_and_reports_success(self, service):
        svc, repo = service
        with patch(
            "app.features.settings.service.telegram.send_message", AsyncMock()
        ) as mock_send:
            result = await svc.send_telegram_test_message()

        mock_send.assert_awaited_once()
        assert result.success is True

    @pytest.mark.asyncio
    async def test_reports_failure_without_touching_the_run_when_telegram_rejects_it(
        self, service
    ):
        svc, repo = service
        with patch(
            "app.features.settings.service.telegram.send_message",
            AsyncMock(side_effect=TelegramError("Unauthorized")),
        ):
            result = await svc.send_telegram_test_message()

        assert result.success is False
        assert "Unauthorized" in result.detail

    @pytest.mark.asyncio
    async def test_refuses_when_telegram_is_not_enabled(self, service):
        svc, repo = service
        repo.get = AsyncMock(return_value=make_settings(telegram_enabled=False))

        result = await svc.send_telegram_test_message()

        assert result.success is False
        assert "Enable" in result.detail

    @pytest.mark.asyncio
    async def test_refuses_when_bot_token_or_chat_id_is_missing(self, service):
        svc, repo = service
        repo.get = AsyncMock(return_value=make_settings(telegram_bot_token=""))

        result = await svc.send_telegram_test_message()

        assert result.success is False
        assert "required" in result.detail
