"""API endpoints for Destination management."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import (
    ConnectionFailedError,
    ConnectorError,
    TableNotFoundError,
)
from app.connectors.factory import UnknownConnectorTypeError
from app.core.database import get_db
from app.core.exceptions import ConflictError, NotFoundError
from app.features.destinations.repository import DestinationRepository
from app.features.destinations.schemas import (
    ConnectionTestResult,
    DestinationCreate,
    DestinationListResponse,
    DestinationRead,
    DestinationUpdate,
    EntityFieldRead,
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


@router.post("/{id}/test-connection", response_model=ConnectionTestResult)
async def test_destination_connection(
    id: int,
    service: DestinationService = Depends(get_destination_service),
):
    """Try to connect to a destination with its stored credentials.

    Unlike the other endpoints below, a failed connection is reported as
    `{"success": false, "message": "..."}` rather than an HTTP error — this
    endpoint exists specifically so the UI can show an inline result
    without treating "bad credentials" as an exceptional app error.
    """
    try:
        await service.test_connection(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnknownConnectorTypeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except ConnectorError as e:
        return ConnectionTestResult(success=False, message=str(e))
    return ConnectionTestResult(success=True, message="Connection successful.")


@router.get("/{id}/entities", response_model=list[str])
async def list_destination_entities(
    id: int,
    service: DestinationService = Depends(get_destination_service),
):
    """List the entity types a destination can receive records as, for the
    mapping UI's entity picker."""
    try:
        return await service.get_entities(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnknownConnectorTypeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except ConnectionFailedError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{id}/entities/{entity}/fields", response_model=list[EntityFieldRead])
async def get_destination_entity_fields(
    id: int,
    entity: str,
    service: DestinationService = Depends(get_destination_service),
):
    """Describe an entity's fields, for the mapping UI's field picker."""
    try:
        return await service.get_entity_fields(id, entity)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except TableNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnknownConnectorTypeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except ConnectionFailedError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
