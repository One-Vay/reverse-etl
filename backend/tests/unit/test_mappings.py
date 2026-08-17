import pytest
from datetime import datetime
from httpx import AsyncClient
from app.features.mappings.schemas import MappingRead, MappingListResponse
from app.core.exceptions import NotFoundError


@pytest.mark.asyncio
async def test_create_mapping(client: AsyncClient, mapping_service):
    payload = {
        "name": "New Map",
        "source_id": 1,
        "source_table": "users",
        "destination_entity": "contacts",
        "field_mappings": [{"source_field": "name", "destination_field": "NAME"}],
    }
    now = datetime.now()
    expected = MappingRead(
        id=1,
        name="New Map",
        source_id=1,
        source_table="users",
        destination_entity="contacts",
        field_mappings=[{"source_field": "name", "destination_field": "NAME"}],
        created_at=now,
        updated_at=now,
    )
    mapping_service.create.return_value = expected

    response = await client.post("/api/v1/mappings/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Map"
    mapping_service.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_mapping_source_not_found(client: AsyncClient, mapping_service):
    mapping_service.create.side_effect = NotFoundError("Source not found")
    payload = {
        "name": "Invalid",
        "source_id": 9999,
        "source_table": "t",
        "destination_entity": "e",
        "field_mappings": [],
    }
    response = await client.post("/api/v1/mappings/", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_mapping(client: AsyncClient, mapping_service):
    now = datetime.now()
    expected = MappingRead(
        id=1,
        name="Test",
        source_id=1,
        source_table="t",
        destination_entity="e",
        field_mappings=[],
        created_at=now,
        updated_at=now,
    )
    mapping_service.get.return_value = expected

    response = await client.get("/api/v1/mappings/1")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_mappings(client: AsyncClient, mapping_service):
    now = datetime.now()
    expected = MappingListResponse(
        items=[
            MappingRead(
                id=1,
                name="Test",
                source_id=1,
                source_table="t",
                destination_entity="e",
                field_mappings=[],
                created_at=now,
                updated_at=now,
            )
        ],
        total=1,
        skip=0,
        limit=100,
    )
    mapping_service.get_list.return_value = expected

    response = await client.get("/api/v1/mappings/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_mapping(client: AsyncClient, mapping_service):
    now = datetime.now()
    expected = MappingRead(
        id=1,
        name="Updated",
        source_id=1,
        source_table="t",
        destination_entity="e",
        field_mappings=[],
        created_at=now,
        updated_at=now,
    )
    mapping_service.update.return_value = expected

    response = await client.put("/api/v1/mappings/1", json={"name": "Updated"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_mapping(client: AsyncClient, mapping_service):
    mapping_service.delete.return_value = None
    response = await client.delete("/api/v1/mappings/1")
    assert response.status_code == 204
