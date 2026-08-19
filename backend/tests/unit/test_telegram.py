"""Unit tests for the Telegram client, with httpx mocked — no real network
access."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.telegram import TelegramError, send_message


def make_response(status_code: int, json_body: dict | None = None, text: str = ""):
    response = MagicMock()
    response.status_code = status_code
    response.is_error = status_code >= 400
    response.text = text
    if json_body is not None:
        response.json = MagicMock(return_value=json_body)
    else:
        response.json = MagicMock(side_effect=ValueError("no json"))
    return response


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_sends_the_expected_payload(self, mock_client):
        mock_client.post = AsyncMock(return_value=make_response(200, {"ok": True}))
        with patch("httpx.AsyncClient", return_value=mock_client):
            await send_message("123:abc", "999", "hello")

        mock_client.post.assert_awaited_once()
        url, kwargs = mock_client.post.call_args
        assert url[0] == "https://api.telegram.org/bot123:abc/sendMessage"
        assert kwargs["json"] == {
            "chat_id": "999",
            "text": "hello",
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

    @pytest.mark.asyncio
    async def test_raises_telegram_error_on_http_failure(self, mock_client):
        mock_client.post = AsyncMock(
            return_value=make_response(
                401, {"description": "Unauthorized"}, text="Unauthorized"
            )
        )
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(TelegramError, match="Unauthorized"):
                await send_message("bad-token", "999", "hello")

    @pytest.mark.asyncio
    async def test_raises_telegram_error_when_unreachable(self, mock_client):
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("boom"))
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(TelegramError, match="Could not reach Telegram"):
                await send_message("123:abc", "999", "hello")

    @pytest.mark.asyncio
    async def test_falls_back_to_raw_text_when_error_body_is_not_json(
        self, mock_client
    ):
        mock_client.post = AsyncMock(
            return_value=make_response(500, json_body=None, text="internal error")
        )
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(TelegramError, match="internal error"):
                await send_message("123:abc", "999", "hello")
