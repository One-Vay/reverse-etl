"""API endpoints for Destination management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.features.destinations.repository import DestinationRepository
from app.features.destinations.schemas import (
    DestinationCreate,
    DestinationListResponse,
    DestinationRead,
    DestinationUpdate,
)
from app.features.destinations.service import DestinationService

router = APIRouter(prefix="/destinations", tags=["destinations"])


async def get_destination_service(
    session: AsyncSession = Depends(get_db),
) -> DestinationService:
    repository = DestinationRepository(session)
    return DestinationService(repository)


@router.get("/", response_model=DestinationListResponse)
async def list_destinations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    name: str | None = None,
    type: str | None = None,
    service: DestinationService = Depends(get_destination_service),
):
    return await service.get_list(skip=skip, limit=limit, name=name, type=type)


@router.get("/{id}", response_model=DestinationRead)
async def get_destination(
    id: int, service: DestinationService = Depends(get_destination_service)
):
    try:
        return await service.get(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/", response_model=DestinationRead, status_code=status.HTTP_201_CREATED)
async def create_destination(
    data: DestinationCreate,
    service: DestinationService = Depends(get_destination_service),
):
    try:
        return await service.create(data)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.put("/{id}", response_model=DestinationRead)
async def update_destination(
    id: int,
    data: DestinationUpdate,
    service: DestinationService = Depends(get_destination_service),
):
    try:
        return await service.update(id, data)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_destination(
    id: int, service: DestinationService = Depends(get_destination_service)
):
    try:
        await service.delete(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
