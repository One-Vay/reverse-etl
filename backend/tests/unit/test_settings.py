"""Router-level tests for AppSettings, with the service mocked."""

from datetime import datetime

import pytest
from httpx import AsyncClient

from app.features.settings.schemas import AppSettingsRead, LLMStatus


def make_settings(**overrides) -> AppSettingsRead:
    defaults = {
        "scheduler_enabled": True,
        "scheduler_poll_interval_seconds": 30,
        "llm_enabled": False,
        "llm_base_url": "http://ollama:11434",
        "llm_model": "qwen2.5:0.5b",
        "default_connect_timeout_seconds": 10.0,
        "default_request_timeout_seconds": 30.0,
        "updated_at": datetime.now(),
    }
    defaults.update(overrides)
    return AppSettingsRead(**defaults)


@pytest.mark.asyncio
async def test_get_settings(client: AsyncClient, settings_service):
    settings_service.get.return_value = make_settings()

    response = await client.get("/api/v1/settings/")

    assert response.status_code == 200
    data = response.json()
    assert data["scheduler_poll_interval_seconds"] == 30


@pytest.mark.asyncio
async def test_update_settings(client: AsyncClient, settings_service):
    settings_service.update.return_value = make_settings(llm_enabled=True)

    response = await client.put("/api/v1/settings/", json={"llm_enabled": True})

    assert response.status_code == 200
    assert response.json()["llm_enabled"] is True
    settings_service.update.assert_called_once()


@pytest.mark.asyncio
async def test_rejects_poll_interval_below_minimum(
    client: AsyncClient, settings_service
):
    response = await client.put(
        "/api/v1/settings/", json={"scheduler_poll_interval_seconds": 1}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_llm_status(client: AsyncClient, settings_service):
    settings_service.get_llm_status.return_value = LLMStatus(
        model_present=True, pulling=False
    )

    response = await client.get("/api/v1/settings/llm/status")

    assert response.status_code == 200
    assert response.json()["model_present"] is True


@pytest.mark.asyncio
async def test_pull_llm_model(client: AsyncClient, settings_service):
    settings_service.get.return_value = make_settings()

    response = await client.post("/api/v1/settings/llm/pull")

    assert response.status_code == 202
    settings_service.trigger_model_pull.assert_called_once()
