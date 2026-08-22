"""Unit tests for AppSettings schema-level validation."""

from app.features.settings.schemas import AppSettingsUpdate


class TestTelegramWhitespaceStripping:
    """A bot token/chat ID pasted with stray leading/trailing whitespace
    (easy to pick up copying from Telegram or a chat app) would otherwise
    be sent to the API verbatim and fail with a confusing "chat not
    found"/401 instead of the obviously-wrong value it actually is."""

    def test_strips_whitespace_from_bot_token(self):
        update = AppSettingsUpdate(telegram_bot_token="  123456:AAExample  \n")
        assert update.telegram_bot_token == "123456:AAExample"

    def test_strips_whitespace_from_chat_id(self):
        update = AppSettingsUpdate(telegram_chat_id=" 123456789 ")
        assert update.telegram_chat_id == "123456789"

    def test_leaves_unset_fields_untouched(self):
        update = AppSettingsUpdate()
        assert update.telegram_bot_token is None
        assert update.telegram_chat_id is None
