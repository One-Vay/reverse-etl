"""API endpoints for Source management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.features.sources.repository import SourceRepository
from app.features.sources.schemas import (
    SourceCreate,
    SourceListResponse,
    SourceRead,
    SourceUpdate,
)
from app.features.sources.service import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])


async def get_source_service(session: AsyncSession = Depends(get_db)) -> SourceService:
    repository = SourceRepository(session)
    return SourceService(repository)


@router.get("/", response_model=SourceListResponse)
async def list_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    name: str | None = None,
    type: str | None = None,
    service: SourceService = Depends(get_source_service),
):
    """List all sources with pagination and filters."""
    return await service.get_list(skip=skip, limit=limit, name=name, type=type)


@router.get("/{id}", response_model=SourceRead)
async def get_source(
    id: int,
    service: SourceService = Depends(get_source_service),
):
    """Get a single source by ID."""
    try:
        return await service.get(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/", response_model=SourceRead, status_code=status.HTTP_201_CREATED)
async def create_source(
    data: SourceCreate,
    service: SourceService = Depends(get_source_service),
):
    """Create a new source."""
    try:
        return await service.create(data)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.put("/{id}", response_model=SourceRead)
async def update_source(
    id: int,
    data: SourceUpdate,
    service: SourceService = Depends(get_source_service),
):
    """Update an existing source."""
    try:
        return await service.update(id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    id: int,
    service: SourceService = Depends(get_source_service),
):
    """Delete a source by ID."""
    try:
        await service.delete(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
