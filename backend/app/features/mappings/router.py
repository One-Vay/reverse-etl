"""API endpoints for Mapping management."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import NotFoundError, ConflictError, ValidationError
from app.features.mappings.repository import MappingRepository
from app.features.sources.repository import SourceRepository
from app.features.mappings.service import MappingService
from app.features.mappings.schemas import MappingCreate, MappingUpdate, MappingRead, MappingListResponse

router = APIRouter(prefix="/mappings", tags=["mappings"])


async def get_mapping_service(session: AsyncSession = Depends(get_db)) -> MappingService:
    mapping_repo = MappingRepository(session)
    source_repo = SourceRepository(session)
    return MappingService(mapping_repo, source_repo)


@router.get("/", response_model=MappingListResponse)
async def list_mappings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    source_id: Optional[int] = None,
    source_table: Optional[str] = None,
    destination_entity: Optional[str] = None,
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(id: int, service: MappingService = Depends(get_mapping_service)):
    try:
        await service.delete(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))