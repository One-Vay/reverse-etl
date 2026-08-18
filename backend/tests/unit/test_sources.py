from datetime import datetime
from unittest.mock import ANY

import pytest
from httpx import AsyncClient

from app.connectors.base import (
    ColumnSchema,
    ConnectionFailedError,
    TableInfo,
    TableNotFoundError,
)
from app.connectors.factory import UnknownConnectorTypeError
from app.core.exceptions import ConflictError, NotFoundError
from app.features.sources.schemas import SourceListResponse, SourceRead

now = datetime.now()


@pytest.mark.asyncio
async def test_create_source(client: AsyncClient, source_service):
    payload = {
        "name": "New Source",
        "type": "postgres",
        "host": "localhost",
        "port": 5432,
        "database": "testdb",
        "username": "user",
        "password": "secret",
    }
    expected = SourceRead(
        id=1,
        name="New Source",
        type="postgres",
        host="localhost",
        port=5432,
        database="testdb",
        username="user",
        created_at=now,
        updated_at=now,
    )
    source_service.create.return_value = expected

    response = await client.post("/api/v1/sources/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Source"
    source_service.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_source_duplicate(client: AsyncClient, source_service):
    source_service.create.side_effect = ConflictError(
        "Source with name 'Test' already exists"
    )
    payload = {
        "name": "Test",
        "type": "postgres",
        "host": "localhost",
        "port": 5432,
        "database": "db",
        "username": "u",
        "password": "p",
    }
    response = await client.post("/api/v1/sources/", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_source(client: AsyncClient, source_service):
    expected = SourceRead(
        id=1,
        name="Test",
        type="postgres",
        host="localhost",
        port=5432,
        database="testdb",
        username="user",
        created_at=now,
        updated_at=now,
    )
    source_service.get.return_value = expected

    response = await client.get("/api/v1/sources/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    source_service.get.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_get_source_not_found(client: AsyncClient, source_service):
    source_service.get.side_effect = NotFoundError("Source not found")
    response = await client.get("/api/v1/sources/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_sources(client: AsyncClient, source_service):
    expected = SourceListResponse(
        items=[
            SourceRead(
                id=1,
                name="Test",
                type="postgres",
                host="localhost",
                port=5432,
                database="db",
                username="u",
                created_at=now,
                updated_at=now,
            )
        ],
        total=1,
        skip=0,
        limit=100,
    )
    source_service.get_list.return_value = expected

    response = await client.get("/api/v1/sources/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    source_service.get_list.assert_called_once_with(
        skip=0, limit=100, name=None, type=None
    )


@pytest.mark.asyncio
async def test_update_source(client: AsyncClient, source_service):
    expected = SourceRead(
        id=1,
        name="Updated",
        type="postgres",
        host="localhost",
        port=5432,
        database="testdb",
        username="user",
        created_at=now,
        updated_at=now,
    )
    source_service.update.return_value = expected

    response = await client.put("/api/v1/sources/1", json={"name": "Updated"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    source_service.update.assert_called_once_with(1, ANY)


@pytest.mark.asyncio
async def test_delete_source(client: AsyncClient, source_service):
    source_service.delete.return_value = None

    response = await client.delete("/api/v1/sources/1")
    assert response.status_code == 204
    source_service.delete.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_source_not_found(client: AsyncClient, source_service):
    source_service.delete.side_effect = NotFoundError("Source not found")
    response = await client.delete("/api/v1/sources/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_test_connection_success(client: AsyncClient, source_service):
    source_service.test_connection.return_value = None

    response = await client.post("/api/v1/sources/1/test-connection")

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Connection successful."}
    source_service.test_connection.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_test_connection_reports_failure_without_error_status(
    client: AsyncClient, source_service
):
    source_service.test_connection.side_effect = ConnectionFailedError(
        "Authentication failed for user 'etl_user'."
    )

    response = await client.post("/api/v1/sources/1/test-connection")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "Authentication failed" in data["message"]


@pytest.mark.asyncio
async def test_test_connection_not_found(client: AsyncClient, source_service):
    source_service.test_connection.side_effect = NotFoundError("Source not found")
    response = await client.post("/api/v1/sources/999/test-connection")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_test_connection_unimplemented_connector(
    client: AsyncClient, source_service
):
    source_service.test_connection.side_effect = NotImplementedError(
        "The ClickHouse connector is not implemented yet."
    )
    response = await client.post("/api/v1/sources/1/test-connection")
    assert response.status_code == 501


@pytest.mark.asyncio
async def test_list_source_tables(client: AsyncClient, source_service):
    source_service.get_tables.return_value = [
        TableInfo(name="contacts", schema="public", kind="table"),
        TableInfo(name="active_contacts", schema="public", kind="view"),
    ]

    response = await client.get("/api/v1/sources/1/tables")

    assert response.status_code == 200
    data = response.json()
    assert data == [
        {"name": "contacts", "schema": "public", "kind": "table"},
        {"name": "active_contacts", "schema": "public", "kind": "view"},
    ]
    source_service.get_tables.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_list_source_tables_connection_failed(
    client: AsyncClient, source_service
):
    source_service.get_tables.side_effect = ConnectionFailedError(
        "Could not reach host"
    )
    response = await client.get("/api/v1/sources/1/tables")
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_list_source_tables_unknown_connector_type(
    client: AsyncClient, source_service
):
    source_service.get_tables.side_effect = UnknownConnectorTypeError("No connector")
    response = await client.get("/api/v1/sources/1/tables")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_source_table_schema(client: AsyncClient, source_service):
    source_service.get_table_schema.return_value = [
        ColumnSchema(
            name="id", data_type="integer", nullable=False, is_primary_key=True
        ),
        ColumnSchema(
            name="email", data_type="text", nullable=False, is_primary_key=False
        ),
    ]

    response = await client.get("/api/v1/sources/1/tables/contacts/schema")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["name"] == "id"
    assert data[0]["is_primary_key"] is True
    source_service.get_table_schema.assert_called_once_with(1, "contacts", "public")


@pytest.mark.asyncio
async def test_get_source_table_schema_respects_schema_query_param(
    client: AsyncClient, source_service
):
    source_service.get_table_schema.return_value = []
    await client.get("/api/v1/sources/1/tables/contacts/schema?schema=reporting")
    source_service.get_table_schema.assert_called_once_with(1, "contacts", "reporting")


@pytest.mark.asyncio
async def test_get_source_table_schema_not_found(client: AsyncClient, source_service):
    source_service.get_table_schema.side_effect = TableNotFoundError("no such table")
    response = await client.get("/api/v1/sources/1/tables/ghost/schema")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_source_table(client: AsyncClient, source_service):
    source_service.preview_table.return_value = [
        {"id": 1, "email": "a@example.com"},
        {"id": 2, "email": "b@example.com"},
    ]

    response = await client.get("/api/v1/sources/1/tables/contacts/preview?limit=2")

    assert response.status_code == 200
    data = response.json()
    assert data["columns"] == ["id", "email"]
    assert len(data["rows"]) == 2
    source_service.preview_table.assert_called_once_with(
        1, "contacts", "public", None, 2
    )


@pytest.mark.asyncio
async def test_preview_source_table_parses_columns_query_param(
    client: AsyncClient, source_service
):
    source_service.preview_table.return_value = []

    await client.get("/api/v1/sources/1/tables/contacts/preview?columns=id,email")

    source_service.preview_table.assert_called_once_with(
        1, "contacts", "public", ["id", "email"], 20
    )


@pytest.mark.asyncio
async def test_preview_source_table_empty_result_uses_requested_columns(
    client: AsyncClient, source_service
):
    source_service.preview_table.return_value = []

    response = await client.get(
        "/api/v1/sources/1/tables/contacts/preview?columns=id,email"
    )

    assert response.json() == {"columns": ["id", "email"], "rows": []}
