import pytest
from datetime import datetime
from httpx import AsyncClient
from app.features.destinations.schemas import DestinationRead, DestinationListResponse
from app.core.exceptions import NotFoundError, ConflictError


@pytest.mark.asyncio
async def test_create_destination(client: AsyncClient, destination_service):
    payload = {
        "name": "New Dest",
        "type": "bitrix24",
        "api_url": "https://test.bitrix24.ru/rest/",
        "auth_token": "token123",
    }
    now = datetime.now()
    expected = DestinationRead(
        id=1,
        name="New Dest",
        type="bitrix24",
        api_url="https://test.bitrix24.ru/rest/",
        created_at=now,
        updated_at=now,
    )
    destination_service.create.return_value = expected

    response = await client.post("/api/v1/destinations/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Dest"
    destination_service.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_destination_duplicate(client: AsyncClient, destination_service):
    destination_service.create.side_effect = ConflictError("Destination exists")
    payload = {
        "name": "Test",
        "type": "bitrix24",
        "api_url": "http://test",
        "auth_token": "t",
    }
    response = await client.post("/api/v1/destinations/", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_destination(client: AsyncClient, destination_service):
    now = datetime.now()
    expected = DestinationRead(
        id=1,
        name="Test",
        type="bitrix24",
        api_url="http://test",
        created_at=now,
        updated_at=now,
    )
    destination_service.get.return_value = expected

    response = await client.get("/api/v1/destinations/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1


@pytest.mark.asyncio
async def test_get_destination_not_found(client: AsyncClient, destination_service):
    destination_service.get.side_effect = NotFoundError("Not found")
    response = await client.get("/api/v1/destinations/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_destinations(client: AsyncClient, destination_service):
    now = datetime.now()
    expected = DestinationListResponse(
        items=[
            DestinationRead(
                id=1,
                name="Test",
                type="bitrix24",
                api_url="http://test",
                created_at=now,
                updated_at=now,
            )
        ],
        total=1,
        skip=0,
        limit=100,
    )
    destination_service.get_list.return_value = expected

    response = await client.get("/api/v1/destinations/")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


@pytest.mark.asyncio
async def test_update_destination(client: AsyncClient, destination_service):
    now = datetime.now()
    expected = DestinationRead(
        id=1,
        name="Updated",
        type="bitrix24",
        api_url="http://test",
        created_at=now,
        updated_at=now,
    )
    destination_service.update.return_value = expected

    response = await client.put("/api/v1/destinations/1", json={"name": "Updated"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_destination(client: AsyncClient, destination_service):
    destination_service.delete.return_value = None
    response = await client.delete("/api/v1/destinations/1")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_destination_not_found(client: AsyncClient, destination_service):
    destination_service.delete.side_effect = NotFoundError("Not found")
    response = await client.delete("/api/v1/destinations/999")
    assert response.status_code == 404
