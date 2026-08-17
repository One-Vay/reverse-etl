from datetime import datetime
from unittest.mock import ANY

import pytest
from httpx import AsyncClient

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
