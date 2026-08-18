"""API endpoints for Source management."""

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
from app.features.sources.repository import SourceRepository
from app.features.sources.schemas import (
    ColumnInfoRead,
    ConnectionTestResult,
    SourceCreate,
    SourceListResponse,
    SourceRead,
    SourceUpdate,
    TableInfoRead,
    TablePreviewResponse,
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


@router.post("/{id}/test-connection", response_model=ConnectionTestResult)
async def test_source_connection(
    id: int,
    service: SourceService = Depends(get_source_service),
):
    """Try to connect to a source with its stored credentials.

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


@router.get("/{id}/tables", response_model=list[TableInfoRead])
async def list_source_tables(
    id: int,
    service: SourceService = Depends(get_source_service),
):
    """List the tables and views visible on a source, for the mapping UI's
    table picker."""
    try:
        return await service.get_tables(id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnknownConnectorTypeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except ConnectionFailedError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{id}/tables/{table_name}/schema", response_model=list[ColumnInfoRead])
async def get_source_table_schema(
    id: int,
    table_name: str,
    schema: str = Query("public", description="Schema the table lives in"),
    service: SourceService = Depends(get_source_service),
):
    """Describe a table's columns, for the mapping UI's column picker."""
    try:
        return await service.get_table_schema(id, table_name, schema)
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


@router.get("/{id}/tables/{table_name}/preview", response_model=TablePreviewResponse)
async def preview_source_table(
    id: int,
    table_name: str,
    schema: str = Query("public", description="Schema the table lives in"),
    columns: str | None = Query(
        None, description="Comma-separated column names; omit for all columns"
    ),
    limit: int = Query(20, ge=1, le=200),
    service: SourceService = Depends(get_source_service),
):
    """Fetch a small row sample from a source table, for previewing data
    while building a field mapping."""
    column_list = [c.strip() for c in columns.split(",")] if columns else None
    try:
        rows = await service.preview_table(id, table_name, schema, column_list, limit)
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

    result_columns = column_list or (list(rows[0].keys()) if rows else [])
    return TablePreviewResponse(columns=result_columns, rows=rows)
