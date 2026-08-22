"""Router-level tests for DataAgent endpoints, with the service mocked."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.core.exceptions import NotFoundError, ValidationError
from app.features.agents.schemas import (
    AgentListResponse,
    AgentRead,
    AgentRunListResponse,
    AgentRunRead,
    LLMModelStatus,
)


def make_agent_read(**overrides) -> AgentRead:
    defaults = {
        "id": 1,
        "name": "Conversion booster",
        "destination_id": 1,
        "mapping_id": 1,
        "goal": "Increase conversion",
        "actions": "Direct calls",
        "feature_notes": [],
        "llm_model": "qwen2.5:0.5b",
        "selection_strategy": "scoring",
        "selection_threshold": 0.6,
        "incremental_field": None,
        "status": "draft",
        "plan": None,
        "plan_generated_at": None,
        "last_run_at": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return AgentRead(**defaults)


def make_run_read(**overrides) -> AgentRunRead:
    defaults = {
        "id": 1,
        "agent_id": 1,
        "agent_name": "Conversion booster",
        "status": "success",
        "started_at": datetime.now(timezone.utc),
        "finished_at": datetime.now(timezone.utc),
        "rows_considered": 10,
        "rows_selected": 3,
        "rows_written": 3,
        "selection_summary": "Selected 3 of 10 rows.",
        "error_message": None,
    }
    defaults.update(overrides)
    return AgentRunRead(**defaults)


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient, agent_service):
    agent_service.get_list.return_value = AgentListResponse(
        items=[make_agent_read()], total=1, skip=0, limit=100
    )

    response = await client.get("/api/v1/agents/")

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_create_agent(client: AsyncClient, agent_service):
    agent_service.create.return_value = make_agent_read()

    response = await client.post(
        "/api/v1/agents/",
        json={
            "name": "Conversion booster",
            "destination_id": 1,
            "mapping_id": 1,
            "goal": "Increase conversion",
            "actions": "Direct calls",
            "llm_model": "qwen2.5:0.5b",
        },
    )

    assert response.status_code == 201
    agent_service.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_agent_rejects_missing_destination(
    client: AsyncClient, agent_service
):
    agent_service.create.side_effect = NotFoundError("Destination with id 99 not found")

    response = await client.post(
        "/api/v1/agents/",
        json={
            "name": "x",
            "destination_id": 99,
            "mapping_id": 1,
            "goal": "g",
            "actions": "a",
            "llm_model": "m",
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_agent_not_found(client: AsyncClient, agent_service):
    agent_service.get.side_effect = NotFoundError("Agent with id 1 not found")

    response = await client.get("/api/v1/agents/1")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_plan(client: AsyncClient, agent_service):
    agent_service.generate_plan.return_value = make_agent_read(
        status="ready", plan={"strategy": "scoring"}
    )

    response = await client.post("/api/v1/agents/1/plan")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_generate_plan_reports_llm_failure_as_bad_gateway(
    client: AsyncClient, agent_service
):
    agent_service.generate_plan.side_effect = ValidationError("Ollama unreachable")

    response = await client.post("/api/v1/agents/1/plan")

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_run_agent_now(client: AsyncClient, agent_service):
    agent_service.run_now.return_value = make_run_read()

    response = await client.post("/api/v1/agents/1/run")

    assert response.status_code == 200
    assert response.json()["rows_written"] == 3


@pytest.mark.asyncio
async def test_run_agent_without_a_plan_is_unprocessable(
    client: AsyncClient, agent_service
):
    agent_service.run_now.side_effect = ValidationError(
        "Generate a plan for this agent before running it."
    )

    response = await client.post("/api/v1/agents/1/run")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_agent_runs(client: AsyncClient, agent_service):
    agent_service.get_runs.return_value = AgentRunListResponse(
        items=[make_run_read()], total=1, skip=0, limit=100
    )

    response = await client.get("/api/v1/agents/1/runs")

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_llm_models(client: AsyncClient, agent_service):
    agent_service.list_llm_models.return_value = ["qwen2.5:0.5b", "llama3:8b"]

    response = await client.get("/api/v1/agents/models")

    assert response.status_code == 200
    assert response.json() == ["qwen2.5:0.5b", "llama3:8b"]


@pytest.mark.asyncio
async def test_get_llm_model_status(client: AsyncClient, agent_service):
    agent_service.get_llm_model_status.return_value = LLMModelStatus(
        model="qwen2.5:0.5b", present=True, pulling=False
    )

    response = await client.get("/api/v1/agents/models/qwen2.5:0.5b/status")

    assert response.status_code == 200
    assert response.json()["present"] is True


@pytest.mark.asyncio
async def test_pull_llm_model(client: AsyncClient, agent_service):
    response = await client.post(
        "/api/v1/agents/models/pull", json={"model": "llama3:8b"}
    )

    assert response.status_code == 202
    agent_service.trigger_model_pull.assert_called_once_with("llama3:8b")


@pytest.mark.asyncio
async def test_delete_agent(client: AsyncClient, agent_service):
    response = await client.delete("/api/v1/agents/1")

    assert response.status_code == 204
