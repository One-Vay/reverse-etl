"""Unit tests for the sync execution engine, with both connectors and all
repositories mocked — no real DB or network access.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connectors.base import ConnectionFailedError
from app.features.syncs import runner
from app.features.syncs.models import IntervalUnit, SyncRunStatus, SyncRunTrigger


def make_sync(**overrides):
    sync = MagicMock()
    sync.id = overrides.get("id", 1)
    sync.source_id = overrides.get("source_id", 10)
    sync.destination_id = overrides.get("destination_id", 20)
    sync.interval_value = overrides.get("interval_value", 1)
    sync.interval_unit = overrides.get("interval_unit", IntervalUnit.HOURS)
    sync.run_at_time = overrides.get("run_at_time", None)
    sync.next_run = overrides.get("next_run", datetime(2026, 1, 1, tzinfo=timezone.utc))
    sync.incremental_field = overrides.get("incremental_field", None)
    sync.last_run = overrides.get("last_run", None)

    mapping = MagicMock()
    mapping.source_table = overrides.get("source_table", "contacts")
    mapping.destination_entity = overrides.get("destination_entity", "lead")
    mapping.field_mappings = overrides.get(
        "field_mappings",
        [{"source_field": "email", "destination_field": "EMAIL", "transformation": ""}],
    )
    sync.mapping = mapping
    return sync


def make_source_connector(rows):
    connector = AsyncMock()
    connector.fetch_data = AsyncMock(return_value=rows)
    connector.__aenter__ = AsyncMock(return_value=connector)
    connector.__aexit__ = AsyncMock(return_value=None)
    return connector


def make_destination_connector(written=1):
    connector = AsyncMock()
    connector.upsert_data = AsyncMock(return_value=written)
    connector.__aenter__ = AsyncMock(return_value=connector)
    connector.__aexit__ = AsyncMock(return_value=None)
    return connector


@pytest.fixture
def mock_session():
    session = MagicMock()
    return session


@pytest.fixture
def mock_run_repo():
    repo = MagicMock()

    async def _create(**kwargs):
        run = MagicMock()
        for key, value in kwargs.items():
            setattr(run, key, value)
        return run

    repo.create = AsyncMock(side_effect=_create)
    return repo


@pytest.fixture
def mock_sync_repo():
    repo = MagicMock()
    repo.update_last_run = AsyncMock()
    repo.update_next_run = AsyncMock()
    return repo


def patch_services(source_connector, destination_connector):
    source_service = MagicMock()
    source_service.build_connector = AsyncMock(return_value=source_connector)
    destination_service = MagicMock()
    destination_service.build_connector = AsyncMock(return_value=destination_connector)

    return (
        patch("app.features.syncs.runner.SourceService", return_value=source_service),
        patch(
            "app.features.syncs.runner.DestinationService",
            return_value=destination_service,
        ),
    )


class TestExecuteSuccess:
    @pytest.mark.asyncio
    async def test_fetches_transforms_and_upserts(
        self, mock_session, mock_run_repo, mock_sync_repo
    ):
        sync = make_sync()
        rows = [{"email": "A@B.COM"}, {"email": "c@d.com"}]
        source_connector = make_source_connector(rows)
        destination_connector = make_destination_connector(written=2)

        patch_source, patch_dest = patch_services(
            source_connector, destination_connector
        )
        with (
            patch_source,
            patch_dest,
            patch(
                "app.features.syncs.runner.SyncRepository", return_value=mock_sync_repo
            ),
            patch(
                "app.features.syncs.runner.SyncRunRepository",
                return_value=mock_run_repo,
            ),
        ):
            run = await runner.execute(
                sync, session=mock_session, trigger=SyncRunTrigger.MANUAL
            )

        assert run.status == SyncRunStatus.SUCCESS
        assert run.records_read == 2
        assert run.records_written == 2
        destination_connector.upsert_data.assert_awaited_once_with(
            "lead", [{"EMAIL": "A@B.COM"}, {"EMAIL": "c@d.com"}]
        )
        mock_sync_repo.update_last_run.assert_awaited_once()
        mock_sync_repo.update_next_run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_applies_transformation_presets(
        self, mock_session, mock_run_repo, mock_sync_repo
    ):
        sync = make_sync(
            field_mappings=[
                {
                    "source_field": "email",
                    "destination_field": "EMAIL",
                    "transformation": "lowercase",
                }
            ]
        )
        source_connector = make_source_connector([{"email": "A@B.COM"}])
        destination_connector = make_destination_connector(written=1)

        patch_source, patch_dest = patch_services(
            source_connector, destination_connector
        )
        with (
            patch_source,
            patch_dest,
            patch(
                "app.features.syncs.runner.SyncRepository", return_value=mock_sync_repo
            ),
            patch(
                "app.features.syncs.runner.SyncRunRepository",
                return_value=mock_run_repo,
            ),
        ):
            await runner.execute(
                sync, session=mock_session, trigger=SyncRunTrigger.MANUAL
            )

        destination_connector.upsert_data.assert_awaited_once_with(
            "lead", [{"EMAIL": "a@b.com"}]
        )

    @pytest.mark.asyncio
    async def test_full_fetch_when_no_incremental_field(
        self, mock_session, mock_run_repo, mock_sync_repo
    ):
        sync = make_sync(incremental_field=None)
        source_connector = make_source_connector([])
        destination_connector = make_destination_connector(written=0)

        patch_source, patch_dest = patch_services(
            source_connector, destination_connector
        )
        with (
            patch_source,
            patch_dest,
            patch(
                "app.features.syncs.runner.SyncRepository", return_value=mock_sync_repo
            ),
            patch(
                "app.features.syncs.runner.SyncRunRepository",
                return_value=mock_run_repo,
            ),
        ):
            await runner.execute(
                sync, session=mock_session, trigger=SyncRunTrigger.MANUAL
            )

        source_connector.fetch_data.assert_awaited_once_with("contacts", where=None)

    @pytest.mark.asyncio
    async def test_incremental_where_uses_last_run_watermark(
        self, mock_session, mock_run_repo, mock_sync_repo
    ):
        last_run = datetime(2026, 1, 1, tzinfo=timezone.utc)
        sync = make_sync(incremental_field="updated_at", last_run=last_run)
        source_connector = make_source_connector([])
        destination_connector = make_destination_connector(written=0)

        patch_source, patch_dest = patch_services(
            source_connector, destination_connector
        )
        with (
            patch_source,
            patch_dest,
            patch(
                "app.features.syncs.runner.SyncRepository", return_value=mock_sync_repo
            ),
            patch(
                "app.features.syncs.runner.SyncRunRepository",
                return_value=mock_run_repo,
            ),
        ):
            await runner.execute(
                sync, session=mock_session, trigger=SyncRunTrigger.MANUAL
            )

        source_connector.fetch_data.assert_awaited_once_with(
            "contacts", where=f"updated_at > '{last_run.isoformat()}'"
        )


class TestExecuteFailure:
    @pytest.mark.asyncio
    async def test_connector_error_is_recorded_not_raised(
        self, mock_session, mock_run_repo, mock_sync_repo
    ):
        sync = make_sync()
        source_service = MagicMock()
        source_service.build_connector = AsyncMock(
            side_effect=ConnectionFailedError("could not connect")
        )

        with (
            patch(
                "app.features.syncs.runner.SourceService", return_value=source_service
            ),
            patch(
                "app.features.syncs.runner.SyncRepository", return_value=mock_sync_repo
            ),
            patch(
                "app.features.syncs.runner.SyncRunRepository",
                return_value=mock_run_repo,
            ),
        ):
            run = await runner.execute(
                sync, session=mock_session, trigger=SyncRunTrigger.SCHEDULED
            )

        assert run.status == SyncRunStatus.FAILED
        assert "could not connect" in run.error_message

    @pytest.mark.asyncio
    async def test_failure_still_updates_last_run_and_next_run(
        self, mock_session, mock_run_repo, mock_sync_repo
    ):
        sync = make_sync()
        source_service = MagicMock()
        source_service.build_connector = AsyncMock(
            side_effect=ConnectionFailedError("boom")
        )

        with (
            patch(
                "app.features.syncs.runner.SourceService", return_value=source_service
            ),
            patch(
                "app.features.syncs.runner.SyncRepository", return_value=mock_sync_repo
            ),
            patch(
                "app.features.syncs.runner.SyncRunRepository",
                return_value=mock_run_repo,
            ),
        ):
            await runner.execute(
                sync, session=mock_session, trigger=SyncRunTrigger.MANUAL
            )

        mock_sync_repo.update_last_run.assert_awaited_once()
        mock_sync_repo.update_next_run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unexpected_error_is_also_recorded_not_raised(
        self, mock_session, mock_run_repo, mock_sync_repo
    ):
        sync = make_sync()
        source_service = MagicMock()
        source_service.build_connector = AsyncMock(
            side_effect=RuntimeError("weird bug")
        )

        with (
            patch(
                "app.features.syncs.runner.SourceService", return_value=source_service
            ),
            patch(
                "app.features.syncs.runner.SyncRepository", return_value=mock_sync_repo
            ),
            patch(
                "app.features.syncs.runner.SyncRunRepository",
                return_value=mock_run_repo,
            ),
        ):
            run = await runner.execute(
                sync, session=mock_session, trigger=SyncRunTrigger.MANUAL
            )

        assert run.status == SyncRunStatus.FAILED


class TestNextRunScheduling:
    """The scheduled cadence must anchor to the sync's own previous
    `next_run`, not to whenever the run actually happened — otherwise a
    late run would push every future occurrence later too, and a long
    outage would trigger a burst of catch-up runs instead of just one."""

    @pytest.mark.asyncio
    async def test_next_run_anchors_to_the_previous_scheduled_time_not_now(
        self, mock_session, mock_run_repo, mock_sync_repo
    ):
        # Scheduled for 2 minutes ago (a normal, on-time run) — the new
        # next_run should be exactly one hour after *that*, not one hour
        # after "now".
        scheduled_for = datetime.now(timezone.utc) - timedelta(minutes=2)
        sync = make_sync(
            interval_value=1, interval_unit=IntervalUnit.HOURS, next_run=scheduled_for
        )
        source_connector = make_source_connector([])
        destination_connector = make_destination_connector(written=0)

        patch_source, patch_dest = patch_services(
            source_connector, destination_connector
        )
        with (
            patch_source,
            patch_dest,
            patch(
                "app.features.syncs.runner.SyncRepository", return_value=mock_sync_repo
            ),
            patch(
                "app.features.syncs.runner.SyncRunRepository",
                return_value=mock_run_repo,
            ),
        ):
            await runner.execute(
                sync, session=mock_session, trigger=SyncRunTrigger.SCHEDULED
            )

        call_id, next_run = mock_sync_repo.update_next_run.call_args.args
        assert call_id == sync.id
        assert next_run == scheduled_for + timedelta(hours=1)

    @pytest.mark.asyncio
    async def test_long_outage_skips_forward_instead_of_bursting(
        self, mock_session, mock_run_repo, mock_sync_repo
    ):
        # The sync was due 3 days ago (e.g. the container was down) with
        # an hourly interval — naively anchoring would produce a next_run
        # still hours in the past, which the scheduler would immediately
        # see as due again on its very next poll. It must land in the
        # future instead.
        scheduled_for = datetime.now(timezone.utc) - timedelta(days=3)
        sync = make_sync(
            interval_value=1, interval_unit=IntervalUnit.HOURS, next_run=scheduled_for
        )
        source_connector = make_source_connector([])
        destination_connector = make_destination_connector(written=0)

        patch_source, patch_dest = patch_services(
            source_connector, destination_connector
        )
        with (
            patch_source,
            patch_dest,
            patch(
                "app.features.syncs.runner.SyncRepository", return_value=mock_sync_repo
            ),
            patch(
                "app.features.syncs.runner.SyncRunRepository",
                return_value=mock_run_repo,
            ),
        ):
            await runner.execute(
                sync, session=mock_session, trigger=SyncRunTrigger.SCHEDULED
            )

        _, next_run = mock_sync_repo.update_next_run.call_args.args
        assert next_run > datetime.now(timezone.utc)
