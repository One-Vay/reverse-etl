import pytest
from datetime import datetime
from httpx import AsyncClient
from app.features.syncs.schemas import SyncRead, SyncListResponse
from app.core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_create_sync(client: AsyncClient, sync_service):
    payload = {
        "name": "New Sync",
        "source_id": 1,
        "destination_id": 1,
        "mapping_id": 1,
        "schedule": "*/30 * * * *",
        "status": "active",
    }
    now = datetime.now()
    expected = SyncRead(
        id=1,
        name="New Sync",
        source_id=1,
        destination_id=1,
        mapping_id=1,
        schedule="*/30 * * * *",
        incremental_field=None,
        last_run=None,
        next_run=None,
        status="active",
        created_at=now,
        updated_at=now,
    )
    sync_service.create.return_value = expected

    response = await client.post("/api/v1/syncs/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Sync"
    sync_service.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_sync_invalid_schedule(client: AsyncClient, sync_service):
    sync_service.create.side_effect = ValidationError("Invalid schedule")
    payload = {
        "name": "Invalid",
        "source_id": 1,
        "destination_id": 1,
        "mapping_id": 1,
        "schedule": "invalid",
        "status": "active",
    }
    response = await client.post("/api/v1/syncs/", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_sync_mapping_wrong_source(client: AsyncClient, sync_service):
    sync_service.create.side_effect = ValidationError(
        "Mapping does not belong to source"
    )
    payload = {
        "name": "Wrong",
        "source_id": 2,
        "destination_id": 1,
        "mapping_id": 1,
        "schedule": "*/30 * * * *",
        "status": "active",
    }
    response = await client.post("/api/v1/syncs/", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_sync(client: AsyncClient, sync_service):
    now = datetime.now()
    expected = SyncRead(
        id=1,
        name="Test",
        source_id=1,
        destination_id=1,
        mapping_id=1,
        schedule="*/30 * * * *",
        incremental_field=None,
        last_run=None,
        next_run=None,
        status="active",
        created_at=now,
        updated_at=now,
    )
    sync_service.get.return_value = expected

    response = await client.get("/api/v1/syncs/1")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_syncs(client: AsyncClient, sync_service):
    now = datetime.now()
    expected = SyncListResponse(
        items=[
            SyncRead(
                id=1,
                name="Test",
                source_id=1,
                destination_id=1,
                mapping_id=1,
                schedule="*/30 * * * *",
                incremental_field=None,
                last_run=None,
                next_run=None,
                status="active",
                created_at=now,
                updated_at=now,
            )
        ],
        total=1,
        skip=0,
        limit=100,
    )
    sync_service.get_list.return_value = expected

    response = await client.get("/api/v1/syncs/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_sync(client: AsyncClient, sync_service):
    now = datetime.now()
    expected = SyncRead(
        id=1,
        name="Updated",
        source_id=1,
        destination_id=1,
        mapping_id=1,
        schedule="*/30 * * * *",
        incremental_field=None,
        last_run=None,
        next_run=None,
        status="active",
        created_at=now,
        updated_at=now,
    )
    sync_service.update.return_value = expected

    response = await client.put("/api/v1/syncs/1", json={"name": "Updated"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_run_sync_now(client: AsyncClient, sync_service):
    sync_service.run_now.return_value = None
    response = await client.post("/api/v1/syncs/1/run")
    assert response.status_code == 202
    sync_service.run_now.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_delete_sync(client: AsyncClient, sync_service):
    sync_service.delete.return_value = None
    response = await client.delete("/api/v1/syncs/1")
    assert response.status_code == 204
