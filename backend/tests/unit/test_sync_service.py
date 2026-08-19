"""Unit tests for SyncService, with repositories mocked.

Regression coverage for a real bug: `next_run` used to be computed and
then silently dropped, because it was stuffed into a `SyncUpdate(...)`
object that had no `next_run` field — Pydantic's default `extra="ignore"`
swallowed it with no error. Fixed by adding a dedicated
`SyncRepository.update_next_run()`, mirroring the existing
`update_last_run()`. These tests assert that method is actually called
with a real, correctly-calculated datetime.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.features.syncs.models import (
    IntervalUnit,
    Sync,
    SyncRun,
    SyncRunStatus,
    SyncRunTrigger,
    SyncStatus,
)
from app.features.syncs.schemas import SyncCreate, SyncUpdate
from app.features.syncs.service import SyncService


def make_sync(**overrides) -> Sync:
    sync = MagicMock(spec=Sync)
    sync.id = overrides.get("id", 1)
    sync.name = overrides.get("name", "Existing sync")
    sync.source_id = overrides.get("source_id", 1)
    sync.destination_id = overrides.get("destination_id", 1)
    sync.mapping_id = overrides.get("mapping_id", 1)
    sync.interval_value = overrides.get("interval_value", 1)
    sync.interval_unit = overrides.get("interval_unit", IntervalUnit.HOURS)
    sync.run_at_time = overrides.get("run_at_time", None)
    sync.next_run = overrides.get("next_run", None)
    sync.incremental_field = overrides.get("incremental_field", None)
    sync.status = overrides.get("status", SyncStatus.ACTIVE)
    # MagicMock(spec=Sync) still auto-generates these relationship attrs as
    # further MagicMocks instead of raising, which then fails SyncRead's
    # nested-schema validation — pin them to what an unloaded relation
    # actually looks like.
    sync.source = None
    sync.destination = None
    sync.mapping = None
    return sync


@pytest.fixture
def repos():
    sync_repo = MagicMock()
    sync_repo.session = MagicMock()
    sync_repo.get_by_id = AsyncMock(return_value=make_sync())
    sync_repo.create = AsyncMock(return_value=make_sync())
    sync_repo.update = AsyncMock(return_value=make_sync())
    sync_repo.update_last_run = AsyncMock(return_value=make_sync())
    sync_repo.update_next_run = AsyncMock(return_value=make_sync())

    source_repo = MagicMock()
    source_repo.get_by_id = AsyncMock(return_value=MagicMock(id=1))

    destination_repo = MagicMock()
    destination_repo.get_by_id = AsyncMock(return_value=MagicMock(id=1))

    mapping_repo = MagicMock()
    mapping_repo.get_by_id = AsyncMock(return_value=MagicMock(id=1, source_id=1))

    run_repo = MagicMock()

    return sync_repo, source_repo, destination_repo, mapping_repo, run_repo


@pytest.fixture
def service(repos):
    sync_repo, source_repo, destination_repo, mapping_repo, run_repo = repos
    return SyncService(sync_repo, source_repo, destination_repo, mapping_repo, run_repo)


class TestCreate:
    @pytest.mark.asyncio
    async def test_persists_the_calculated_next_run(self, service, repos):
        sync_repo, *_ = repos
        data = SyncCreate(
            name="Hourly sync",
            source_id=1,
            destination_id=1,
            mapping_id=1,
            interval_value=1,
            interval_unit="hours",
        )

        await service.create(data)

        sync_repo.update_next_run.assert_awaited_once()
        call_id, call_next_run = sync_repo.update_next_run.call_args.args
        assert call_id == 1
        assert isinstance(call_next_run, datetime)
        assert call_next_run > datetime.now(timezone.utc)


class TestUpdate:
    @pytest.mark.asyncio
    async def test_recalculates_next_run_when_interval_changes(self, service, repos):
        sync_repo, *_ = repos

        await service.update(1, SyncUpdate(interval_value=6, interval_unit="hours"))

        sync_repo.update_next_run.assert_awaited_once()
        call_id, call_next_run = sync_repo.update_next_run.call_args.args
        assert call_id == 1
        assert isinstance(call_next_run, datetime)

    @pytest.mark.asyncio
    async def test_recalculates_next_run_when_run_at_time_changes(self, service, repos):
        sync_repo, *_ = repos

        await service.update(1, SyncUpdate(run_at_time="14:30"))

        sync_repo.update_next_run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_does_not_touch_next_run_for_unrelated_field_changes(
        self, service, repos
    ):
        sync_repo, *_ = repos

        await service.update(1, SyncUpdate(name="Renamed"))

        sync_repo.update_next_run.assert_not_awaited()

    def test_rejects_a_malformed_run_at_time_at_the_schema_level(self):
        with pytest.raises(ValueError, match="HH:MM"):
            SyncUpdate(run_at_time="not a time")

    def test_rejects_an_out_of_range_interval_value_at_the_schema_level(self):
        with pytest.raises(ValueError):
            SyncCreate(
                name="x",
                source_id=1,
                destination_id=1,
                mapping_id=1,
                interval_value=0,
                interval_unit="hours",
            )


class TestRunNow:
    @pytest.mark.asyncio
    async def test_delegates_to_the_runner_and_returns_its_result(self, service, repos):
        sync_repo, *_ = repos
        fake_sync = make_sync()
        sync_repo.get_by_id = AsyncMock(return_value=fake_sync)
        fake_run = MagicMock(spec=SyncRun)
        fake_run.id = 1
        fake_run.sync_id = 1
        fake_run.status = SyncRunStatus.SUCCESS
        fake_run.trigger = SyncRunTrigger.MANUAL
        fake_run.started_at = datetime.now(timezone.utc)
        fake_run.finished_at = datetime.now(timezone.utc)
        fake_run.records_read = 3
        fake_run.records_written = 3
        fake_run.error_message = None
        fake_run.sync_name = fake_sync.name

        with patch(
            "app.features.syncs.service.runner.execute",
            AsyncMock(return_value=fake_run),
        ) as mock_execute:
            result = await service.run_now(1)

        mock_execute.assert_awaited_once_with(
            fake_sync, session=sync_repo.session, trigger=SyncRunTrigger.MANUAL
        )
        assert result.records_written == 3
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_raises_not_found_for_a_missing_sync(self, service, repos):
        sync_repo, *_ = repos
        sync_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.run_now(999)


class TestGetListStatusFilter:
    @pytest.mark.asyncio
    async def test_parses_a_valid_status_string(self, service, repos):
        sync_repo, *_ = repos
        sync_repo.get_count = AsyncMock(return_value=0)
        sync_repo.get_all = AsyncMock(return_value=[])

        await service.get_list(status="paused")

        sync_repo.get_count.assert_awaited_once_with(
            source_id=None,
            destination_id=None,
            mapping_id=None,
            status=SyncStatus.PAUSED,
            search=None,
        )

    @pytest.mark.asyncio
    async def test_rejects_an_invalid_status_string(self, service):
        with pytest.raises(ValidationError, match="archived"):
            await service.get_list(status="archived")
