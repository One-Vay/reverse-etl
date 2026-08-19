"""API endpoints for Mapping management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, ValidationError
from app.features.mappings.repository import MappingRepository
from app.features.mappings.schemas import (
    MappingCreate,
    MappingListResponse,
    MappingRead,
    MappingUpdate,
    SuggestMappingsRequest,
    SuggestMappingsResponse,
)
from app.features.mappings.service import MappingService
from app.features.mappings.suggest import suggest_mappings
from app.features.settings.repository import SettingsRepository
from app.features.settings.schemas import AppSettingsRead
from app.features.sources.repository import SourceRepository

router = APIRouter(prefix="/mappings", tags=["mappings"])


async def get_mapping_service(
    session: AsyncSession = Depends(get_db),
) -> MappingService:
    mapping_repo = MappingRepository(session)
    source_repo = SourceRepository(session)
    return MappingService(mapping_repo, source_repo)


@router.get("/", response_model=MappingListResponse)
async def list_mappings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    source_id: int | None = None,
    source_table: str | None = None,
    destination_entity: str | None = None,
    service: MappingService = Depends(get_mapping_service),
):
    return await service.get_list(
        skip=skip,
        limit=limit,
        source_id=source_id,
        source_table=source_table,
        destination_entity=destination_entity,
    )


@router.get("/{id}", response_model=MappingRead)
async def get_mapping(id: int, service: MappingService = Depends(get_mapping_service)):
    try:
        return await service.get(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/", response_model=MappingRead, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    data: MappingCreate,
    service: MappingService = Depends(get_mapping_service),
):
    try:
        return await service.create(data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.post("/suggest", response_model=SuggestMappingsResponse)
async def suggest_mapping_fields(
    data: SuggestMappingsRequest,
    session: AsyncSession = Depends(get_db),
):
    """AI-suggested source→destination field pairings, for the mapping
    board's "Suggest with AI" button. Always returns 200 — an empty
    `pairs` list with a `message` means suggestions aren't available
    right now (disabled in Settings, or the LLM is unreachable), not an
    error the frontend needs to handle specially."""
    settings_row = await SettingsRepository(session).get()
    settings = AppSettingsRead.model_validate(settings_row)
    return await suggest_mappings(
        data.source_columns, data.destination_fields, settings=settings
    )


@router.put("/{id}", response_model=MappingRead)
async def update_mapping(
    id: int,
    data: MappingUpdate,
    service: MappingService = Depends(get_mapping_service),
):
    try:
        return await service.update(id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    id: int, service: MappingService = Depends(get_mapping_service)
):
    try:
        await service.delete(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
