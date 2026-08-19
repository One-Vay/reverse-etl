"""API endpoints for Sync management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError, ValidationError
from app.features.destinations.repository import DestinationRepository
from app.features.mappings.repository import MappingRepository
from app.features.sources.repository import SourceRepository
from app.features.syncs.repository import SyncRepository, SyncRunRepository
from app.features.syncs.schemas import (
    SyncCreate,
    SyncListResponse,
    SyncRead,
    SyncRunListResponse,
    SyncRunRead,
    SyncUpdate,
)
from app.features.syncs.service import SyncService

router = APIRouter(prefix="/syncs", tags=["syncs"])


async def get_sync_service(session: AsyncSession = Depends(get_db)) -> SyncService:
    sync_repo = SyncRepository(session)
    source_repo = SourceRepository(session)
    dest_repo = DestinationRepository(session)
    mapping_repo = MappingRepository(session)
    run_repo = SyncRunRepository(session)
    return SyncService(sync_repo, source_repo, dest_repo, mapping_repo, run_repo)


@router.get("/", response_model=SyncListResponse)
async def list_syncs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    source_id: int | None = None,
    destination_id: int | None = None,
    mapping_id: int | None = None,
    sync_status: str | None = Query(None, alias="status"),
    search: str | None = None,
    service: SyncService = Depends(get_sync_service),
):
    try:
        return await service.get_list(
            skip=skip,
            limit=limit,
            source_id=source_id,
            destination_id=destination_id,
            mapping_id=mapping_id,
            status=sync_status,
            search=search,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.get("/runs", response_model=SyncRunListResponse)
async def list_all_sync_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SyncService = Depends(get_sync_service),
):
    """History of every sync run across all pipelines, newest first — for
    the dashboard. Registered before `/{id}` so "runs" isn't parsed as an
    id."""
    return await service.get_all_runs(skip=skip, limit=limit)


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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


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
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sync(id: int, service: SyncService = Depends(get_sync_service)):
    try:
        await service.delete(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{id}/run", response_model=SyncRunRead)
async def run_sync_now(id: int, service: SyncService = Depends(get_sync_service)):
    """Run a sync immediately: reads the source, applies the mapping, and
    writes to the destination, synchronously within this request (no task
    queue at this project's scale). Returns the resulting `SyncRun` —
    check its `status`/`error_message` for whether it actually succeeded,
    the HTTP status only reflects that the sync itself was found."""
    try:
        return await service.run_now(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{id}/runs", response_model=SyncRunListResponse)
async def list_sync_runs(
    id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SyncService = Depends(get_sync_service),
):
    try:
        return await service.get_runs(id, skip=skip, limit=limit)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
