"""API endpoints for Sync management."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import NotFoundError, ConflictError, ValidationError
from app.features.syncs.repository import SyncRepository
from app.features.sources.repository import SourceRepository
from app.features.destinations.repository import DestinationRepository
from app.features.mappings.repository import MappingRepository
from app.features.syncs.service import SyncService
from app.features.syncs.schemas import SyncCreate, SyncUpdate, SyncRead, SyncListResponse

router = APIRouter(prefix="/syncs", tags=["syncs"])


async def get_sync_service(session: AsyncSession = Depends(get_db)) -> SyncService:
    sync_repo = SyncRepository(session)
    source_repo = SourceRepository(session)
    dest_repo = DestinationRepository(session)
    mapping_repo = MappingRepository(session)
    return SyncService(sync_repo, source_repo, dest_repo, mapping_repo)


@router.get("/", response_model=SyncListResponse)
async def list_syncs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    source_id: Optional[int] = None,
    destination_id: Optional[int] = None,
    mapping_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    service: SyncService = Depends(get_sync_service),
):
    return await service.get_list(
        skip=skip,
        limit=limit,
        source_id=source_id,
        destination_id=destination_id,
        mapping_id=mapping_id,
        status=status,
        search=search,
    )


@router.get("/{id}", response_model=SyncRead)
async def get_sync(id: int, service: SyncService = Depends(get_sync_service)):
    try:
        return await service.get(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/", response_model=SyncRead, status_code=status.HTTP_201_CREATED)
async def create_sync(
    data: SyncCreate,
    service: SyncService = Depends(get_sync_service),
):
    try:
        return await service.create(data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.put("/{id}", response_model=SyncRead)
async def update_sync(
    id: int,
    data: SyncUpdate,
    service: SyncService = Depends(get_sync_service),
):
    try:
        return await service.update(id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sync(id: int, service: SyncService = Depends(get_sync_service)):
    try:
        await service.delete(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_sync_now(id: int, service: SyncService = Depends(get_sync_service)):
    """Manually trigger a sync job."""
    try:
        await service.run_now(id)
        return {"message": f"Sync {id} triggered successfully"}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))