"""API endpoints for DataAgent management: CRUD, LLM plan generation,
running the selection+sync pipeline, and per-agent local-LLM model
management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, ValidationError
from app.features.agents.repository import AgentRepository, AgentRunRepository
from app.features.agents.schemas import (
    AgentCreate,
    AgentListResponse,
    AgentRead,
    AgentRunListResponse,
    AgentRunRead,
    AgentUpdate,
    LLMModelPullRequest,
    LLMModelStatus,
)
from app.features.agents.service import AgentService
from app.features.destinations.repository import DestinationRepository
from app.features.mappings.repository import MappingRepository
from app.features.settings.repository import SettingsRepository

router = APIRouter(prefix="/agents", tags=["agents"])


async def get_agent_service(session: AsyncSession = Depends(get_db)) -> AgentService:
    return AgentService(
        AgentRepository(session),
        DestinationRepository(session),
        MappingRepository(session),
        AgentRunRepository(session),
        SettingsRepository(session),
    )


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: AgentService = Depends(get_agent_service),
):
    return await service.get_list(skip=skip, limit=limit)


@router.get("/models", response_model=list[str])
async def list_llm_models(service: AgentService = Depends(get_agent_service)):
    """Models already pulled onto the configured Ollama server, for the
    agent form's model picker. Registered before `/{id}` so "models" isn't
    parsed as an id."""
    try:
        return await service.list_llm_models()
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/models/{model}/status", response_model=LLMModelStatus)
async def get_llm_model_status(
    model: str, service: AgentService = Depends(get_agent_service)
):
    """Whether `model` is downloaded and ready, or currently being pulled
    — the frontend polls this after triggering a pull."""
    return await service.get_llm_model_status(model)


@router.post("/models/pull", status_code=status.HTTP_202_ACCEPTED)
async def pull_llm_model(
    data: LLMModelPullRequest, service: AgentService = Depends(get_agent_service)
):
    """Trigger a pull of any named Ollama model, without waiting for it —
    poll `/agents/models/{model}/status` for progress."""
    await service.trigger_model_pull(data.model)
    return {"message": f"Pulling {data.model}"}


@router.get("/{id}", response_model=AgentRead)
async def get_agent(id: int, service: AgentService = Depends(get_agent_service)):
    try:
        return await service.get(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentCreate, service: AgentService = Depends(get_agent_service)
):
    try:
        return await service.create(data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{id}", response_model=AgentRead)
async def update_agent(
    id: int, data: AgentUpdate, service: AgentService = Depends(get_agent_service)
):
    try:
        return await service.update(id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(id: int, service: AgentService = Depends(get_agent_service)):
    try:
        await service.delete(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{id}/plan", response_model=AgentRead)
async def generate_agent_plan(
    id: int, service: AgentService = Depends(get_agent_service)
):
    """Ask the agent's LLM to analyze its goal against the source table
    and propose a plan — a strategy, a plain-language selection rule, and
    recommended next actions. Replaces any previous plan."""
    try:
        return await service.generate_plan(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/{id}/run", response_model=AgentRunRead)
async def run_agent_now(id: int, service: AgentService = Depends(get_agent_service)):
    """Run the agent's selection+sync pipeline immediately: score newly-
    arrived rows against its goal, and write only the selected subset to
    the destination. Returns the resulting `AgentRun` — check its
    `status`/`error_message` for whether it actually succeeded, the HTTP
    status only reflects that the agent was found and had a plan."""
    try:
        return await service.run_now(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.get("/{id}/runs", response_model=AgentRunListResponse)
async def list_agent_runs(
    id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: AgentService = Depends(get_agent_service),
):
    try:
        return await service.get_runs(id, skip=skip, limit=limit)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
