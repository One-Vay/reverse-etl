"""API endpoints for application settings and the local-LLM feature."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.settings.repository import SettingsRepository
from app.features.settings.schemas import AppSettingsRead, AppSettingsUpdate, LLMStatus
from app.features.settings.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


async def get_settings_service(
    session: AsyncSession = Depends(get_db),
) -> SettingsService:
    return SettingsService(SettingsRepository(session))


@router.get("/", response_model=AppSettingsRead)
async def get_settings(service: SettingsService = Depends(get_settings_service)):
    return await service.get()


@router.put("/", response_model=AppSettingsRead)
async def update_settings(
    data: AppSettingsUpdate,
    service: SettingsService = Depends(get_settings_service),
):
    return await service.update(data)


@router.get("/llm/status", response_model=LLMStatus)
async def get_llm_status(service: SettingsService = Depends(get_settings_service)):
    """Whether the configured Ollama model is downloaded and ready — the
    frontend polls this after enabling AI suggestions."""
    return await service.get_llm_status()


@router.post("/llm/pull", status_code=status.HTTP_202_ACCEPTED)
async def pull_llm_model(service: SettingsService = Depends(get_settings_service)):
    """Manually (re)trigger a model pull, without waiting for it — poll
    `/settings/llm/status` for progress."""
    current = await service.get()
    service.trigger_model_pull(current.llm_base_url, current.llm_model)
    return {"message": f"Pulling {current.llm_model}"}
