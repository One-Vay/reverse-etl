"""Unit tests for the advanced, per-connection connector parameters
(timeouts/pool sizes) actually reaching the connector constructor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.features.destinations.service import DestinationService
from app.features.sources.service import SourceService


def make_source(**overrides):
    source = MagicMock()
    source.type = overrides.get("type", "postgres")
    source.host = "db.internal"
    source.port = 5432
    source.database = "analytics"
    source.username = "etl"
    source.password = "encrypted"
    source.connect_timeout = overrides.get("connect_timeout")
    source.command_timeout = overrides.get("command_timeout")
    source.min_pool_size = overrides.get("min_pool_size")
    source.max_pool_size = overrides.get("max_pool_size")
    return source


class TestSourceAdvancedParams:
    @pytest.mark.asyncio
    async def test_omits_unset_advanced_params(self):
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=make_source())
        service = SourceService(repo)

        with (
            patch("app.features.sources.service.decrypt_password", return_value="pw"),
            patch(
                "app.features.sources.service.ConnectorFactory.create_source_connector"
            ) as mock_create,
        ):
            await service.build_connector(1)

        _, kwargs = mock_create.call_args
        assert "connect_timeout" not in kwargs
        assert "min_pool_size" not in kwargs

    @pytest.mark.asyncio
    async def test_forwards_set_advanced_params_for_postgres(self):
        repo = MagicMock()
        repo.get_by_id = AsyncMock(
            return_value=make_source(
                connect_timeout=5.0,
                command_timeout=20.0,
                min_pool_size=2,
                max_pool_size=8,
            )
        )
        service = SourceService(repo)

        with (
            patch("app.features.sources.service.decrypt_password", return_value="pw"),
            patch(
                "app.features.sources.service.ConnectorFactory.create_source_connector"
            ) as mock_create,
        ):
            await service.build_connector(1)

        _, kwargs = mock_create.call_args
        assert kwargs["connect_timeout"] == 5.0
        assert kwargs["command_timeout"] == 20.0
        assert kwargs["min_pool_size"] == 2
        assert kwargs["max_pool_size"] == 8

    @pytest.mark.asyncio
    async def test_clickhouse_only_forwards_connect_timeout(self):
        repo = MagicMock()
        repo.get_by_id = AsyncMock(
            return_value=make_source(
                type="clickhouse",
                connect_timeout=5.0,
                min_pool_size=2,  # not a ClickHouse param — must not be forwarded
            )
        )
        service = SourceService(repo)

        with (
            patch("app.features.sources.service.decrypt_password", return_value="pw"),
            patch(
                "app.features.sources.service.ConnectorFactory.create_source_connector"
            ) as mock_create,
        ):
            await service.build_connector(1)

        _, kwargs = mock_create.call_args
        assert kwargs["connect_timeout"] == 5.0
        assert "min_pool_size" not in kwargs


class TestDestinationAdvancedParams:
    @pytest.mark.asyncio
    async def test_omits_unset_request_timeout(self):
        destination = MagicMock()
        destination.type = "bitrix24"
        destination.api_url = "https://x.bitrix24.ru"
        destination.auth_token = "encrypted"
        destination.request_timeout = None
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=destination)
        service = DestinationService(repo)

        with (
            patch(
                "app.features.destinations.service.decrypt_password", return_value="tok"
            ),
            patch(
                "app.features.destinations.service.ConnectorFactory.create_destination_connector"
            ) as mock_create,
        ):
            await service.build_connector(1)

        _, kwargs = mock_create.call_args
        assert "request_timeout" not in kwargs

    @pytest.mark.asyncio
    async def test_forwards_set_request_timeout(self):
        destination = MagicMock()
        destination.type = "bitrix24"
        destination.api_url = "https://x.bitrix24.ru"
        destination.auth_token = "encrypted"
        destination.request_timeout = 15.0
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=destination)
        service = DestinationService(repo)

        with (
            patch(
                "app.features.destinations.service.decrypt_password", return_value="tok"
            ),
            patch(
                "app.features.destinations.service.ConnectorFactory.create_destination_connector"
            ) as mock_create,
        ):
            await service.build_connector(1)

        _, kwargs = mock_create.call_args
        assert kwargs["request_timeout"] == 15.0
