"""Unit tests for the Ollama client, with httpx fully mocked."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core import llm


def make_response(
    status_code=200, json_data=None, text: str | None = None
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.is_error = status_code >= 400
    response.text = text if text is not None else str(json_data)
    response.json = MagicMock(return_value=json_data if json_data is not None else {})
    return response


def make_mock_client(response: MagicMock) -> MagicMock:
    client = MagicMock()
    client.post = AsyncMock(return_value=response)
    client.get = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


class TestGenerateJson:
    @pytest.mark.asyncio
    async def test_parses_the_nested_response_field(self):
        response = make_response(
            json_data={"response": '{"pairs": [{"source_field": "email"}]}'}
        )
        client = make_mock_client(response)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            result = await llm.generate_json("prompt", model="m", base_url="http://x")

        assert result == {"pairs": [{"source_field": "email"}]}

    @pytest.mark.asyncio
    async def test_network_failure_raises_llm_unavailable(self):
        client = MagicMock()
        client.post = AsyncMock(side_effect=httpx.ConnectTimeout("timed out"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            with pytest.raises(llm.LLMUnavailableError):
                await llm.generate_json("prompt", model="m", base_url="http://x")

    @pytest.mark.asyncio
    async def test_http_error_status_raises_llm_unavailable(self):
        response = make_response(status_code=404, text="not found")
        client = make_mock_client(response)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            with pytest.raises(llm.LLMUnavailableError):
                await llm.generate_json(
                    "prompt", model="missing-model", base_url="http://x"
                )

    @pytest.mark.asyncio
    async def test_malformed_json_response_raises_llm_unavailable(self):
        response = make_response(json_data={"response": "not valid json"})
        client = make_mock_client(response)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            with pytest.raises(llm.LLMUnavailableError):
                await llm.generate_json("prompt", model="m", base_url="http://x")


class TestIsModelPresent:
    @pytest.mark.asyncio
    async def test_true_when_model_name_matches(self):
        response = make_response(json_data={"models": [{"name": "qwen2.5:0.5b"}]})
        client = make_mock_client(response)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            result = await llm.is_model_present("qwen2.5:0.5b", base_url="http://x")
        assert result is True

    @pytest.mark.asyncio
    async def test_false_when_model_not_in_list(self):
        response = make_response(json_data={"models": [{"name": "other-model"}]})
        client = make_mock_client(response)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            result = await llm.is_model_present("qwen2.5:0.5b", base_url="http://x")
        assert result is False

    @pytest.mark.asyncio
    async def test_false_when_ollama_unreachable(self):
        client = MagicMock()
        client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            result = await llm.is_model_present("m", base_url="http://x")
        assert result is False


class TestListModels:
    @pytest.mark.asyncio
    async def test_returns_the_installed_model_names(self):
        response = make_response(
            json_data={"models": [{"name": "qwen2.5:0.5b"}, {"model": "llama3:8b"}]}
        )
        client = make_mock_client(response)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            result = await llm.list_models(base_url="http://x")
        assert result == ["qwen2.5:0.5b", "llama3:8b"]

    @pytest.mark.asyncio
    async def test_empty_when_no_models_installed(self):
        response = make_response(json_data={"models": []})
        client = make_mock_client(response)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            result = await llm.list_models(base_url="http://x")
        assert result == []

    @pytest.mark.asyncio
    async def test_raises_when_unreachable(self):
        client = MagicMock()
        client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            with pytest.raises(llm.LLMUnavailableError):
                await llm.list_models(base_url="http://x")

    @pytest.mark.asyncio
    async def test_raises_on_http_error_status(self):
        response = make_response(status_code=500, text="boom")
        client = make_mock_client(response)
        with patch("app.core.llm.httpx.AsyncClient", return_value=client):
            with pytest.raises(llm.LLMUnavailableError):
                await llm.list_models(base_url="http://x")
