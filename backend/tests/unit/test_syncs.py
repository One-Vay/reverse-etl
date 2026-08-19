import pytest
from datetime import datetime
from httpx import AsyncClient
from app.features.syncs.schemas import SyncRead, SyncListResponse, SyncRunRead
from app.core.exceptions import ValidationError, NotFoundError


def make_sync_read(**overrides) -> SyncRead:
    now = datetime.now()
    defaults = dict(
        id=1,
        name="Test",
        source_id=1,
        destination_id=1,
        mapping_id=1,
        interval_value=1,
        interval_unit="hours",
        run_at_time=None,
        incremental_field=None,
        last_run=None,
        next_run=None,
        status="active",
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return SyncRead(**defaults)


@pytest.mark.asyncio
async def test_create_sync(client: AsyncClient, sync_service):
    payload = {
        "name": "New Sync",
        "source_id": 1,
        "destination_id": 1,
        "mapping_id": 1,
        "interval_value": 6,
        "interval_unit": "hours",
        "status": "active",
    }
    sync_service.create.return_value = make_sync_read(name="New Sync")

    response = await client.post("/api/v1/syncs/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Sync"
    sync_service.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_sync_rejects_interval_value_out_of_range(
    client: AsyncClient, sync_service
):
    payload = {
        "name": "Invalid",
        "source_id": 1,
        "destination_id": 1,
        "mapping_id": 1,
        "interval_value": 0,
        "interval_unit": "hours",
        "status": "active",
    }
    response = await client.post("/api/v1/syncs/", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_sync_rejects_malformed_run_at_time(
    client: AsyncClient, sync_service
):
    payload = {
        "name": "Invalid",
        "source_id": 1,
        "destination_id": 1,
        "mapping_id": 1,
        "interval_value": 1,
        "interval_unit": "days",
        "run_at_time": "not-a-time",
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
        "interval_value": 1,
        "interval_unit": "hours",
        "status": "active",
    }
    response = await client.post("/api/v1/syncs/", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_sync(client: AsyncClient, sync_service):
    sync_service.get.return_value = make_sync_read()

    response = await client.get("/api/v1/syncs/1")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_syncs(client: AsyncClient, sync_service):
    sync_service.get_list.return_value = SyncListResponse(
        items=[make_sync_read()], total=1, skip=0, limit=100
    )

    response = await client.get("/api/v1/syncs/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_sync(client: AsyncClient, sync_service):
    sync_service.update.return_value = make_sync_read(name="Updated")

    response = await client.put("/api/v1/syncs/1", json={"name": "Updated"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_sync_interval(client: AsyncClient, sync_service):
    sync_service.update.return_value = make_sync_read(
        interval_value=2, interval_unit="days", run_at_time="14:30"
    )

    response = await client.put(
        "/api/v1/syncs/1",
        json={"interval_value": 2, "interval_unit": "days", "run_at_time": "14:30"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["interval_unit"] == "days"
    assert data["run_at_time"] == "14:30"


@pytest.mark.asyncio
async def test_run_sync_now(client: AsyncClient, sync_service):
    now = datetime.now()
    expected = SyncRunRead(
        id=1,
        sync_id=1,
        status="success",
        trigger="manual",
        started_at=now,
        finished_at=now,
        records_read=5,
        records_written=5,
        error_message=None,
    )
    sync_service.run_now.return_value = expected

    response = await client.post("/api/v1/syncs/1/run")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["records_written"] == 5
    sync_service.run_now.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_run_sync_now_not_found(client: AsyncClient, sync_service):
    sync_service.run_now.side_effect = NotFoundError("Sync not found")
    response = await client.post("/api/v1/syncs/999/run")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_sync_runs(client: AsyncClient, sync_service):
    now = datetime.now()
    from app.features.syncs.schemas import SyncRunListResponse

    sync_service.get_runs.return_value = SyncRunListResponse(
        items=[
            SyncRunRead(
                id=1,
                sync_id=1,
                status="success",
                trigger="scheduled",
                started_at=now,
                finished_at=now,
                records_read=3,
                records_written=3,
                error_message=None,
            )
        ],
        total=1,
        skip=0,
        limit=100,
    )

    response = await client.get("/api/v1/syncs/1/runs")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    sync_service.get_runs.assert_called_once_with(1, skip=0, limit=100)


@pytest.mark.asyncio
async def test_list_all_sync_runs(client: AsyncClient, sync_service):
    from app.features.syncs.schemas import SyncRunListResponse

    sync_service.get_all_runs.return_value = SyncRunListResponse(
        items=[], total=0, skip=0, limit=100
    )

    response = await client.get("/api/v1/syncs/runs")

    assert response.status_code == 200
    sync_service.get_all_runs.assert_called_once_with(skip=0, limit=100)


@pytest.mark.asyncio
async def test_list_upcoming_sync_runs(client: AsyncClient, sync_service):
    from app.features.syncs.schemas import UpcomingSyncRuns

    now = datetime.now()
    sync_service.get_upcoming.return_value = [
        UpcomingSyncRuns(sync_id=1, sync_name="Test", occurrences=[now])
    ]

    response = await client.get("/api/v1/syncs/upcoming")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["sync_id"] == 1
    sync_service.get_upcoming.assert_called_once_with(days=7)


@pytest.mark.asyncio
async def test_delete_sync(client: AsyncClient, sync_service):
    sync_service.delete.return_value = None
    response = await client.delete("/api/v1/syncs/1")
    assert response.status_code == 204
