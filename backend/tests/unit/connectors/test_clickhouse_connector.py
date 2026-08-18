"""Unit tests for ClickHouseConnector, with clickhouse_connect fully mocked.

These tests never touch a real database — see
tests/integration/test_clickhouse_connector_integration.py for that.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from clickhouse_connect.driver.exceptions import (
    DatabaseError,
    Error,
    OperationalError,
)

from app.connectors.base import (
    ColumnSchema,
    ConnectionFailedError,
    NotConnectedError,
    TableInfo,
    TableNotFoundError,
)
from app.connectors.sources.clickhouse import ClickHouseConnector, _quote_identifier


def make_connector(**overrides) -> ClickHouseConnector:
    params = {
        "host": "ch.internal",
        "port": 8123,
        "database": "analytics",
        "username": "etl_user",
        "password": "s3cret",
    }
    params.update(overrides)
    return ClickHouseConnector(**params)


def make_query_result(column_names=(), result_rows=()) -> MagicMock:
    result = MagicMock()
    result.column_names = column_names
    result.result_rows = result_rows
    return result


def make_mock_client() -> MagicMock:
    client = MagicMock()
    client.query = AsyncMock(return_value=make_query_result())
    client.ping = AsyncMock(return_value=True)
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_get_async_client():
    client = make_mock_client()
    with patch(
        "app.connectors.sources.clickhouse.clickhouse_connect.get_async_client",
        AsyncMock(return_value=client),
    ) as get_async_client:
        yield get_async_client, client


class TestConnect:
    @pytest.mark.asyncio
    async def test_connects_with_expected_parameters(self, mock_get_async_client):
        get_async_client, _ = mock_get_async_client
        connector = make_connector(host="ch.internal", port=8124, database="analytics")

        await connector.connect()

        get_async_client.assert_awaited_once()
        _, kwargs = get_async_client.call_args
        assert kwargs["host"] == "ch.internal"
        assert kwargs["port"] == 8124
        assert kwargs["database"] == "analytics"
        assert kwargs["username"] == "etl_user"
        assert kwargs["password"] == "s3cret"

    @pytest.mark.asyncio
    async def test_is_idempotent(self, mock_get_async_client):
        get_async_client, _ = mock_get_async_client
        connector = make_connector()

        await connector.connect()
        await connector.connect()

        get_async_client.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unreachable_host_raises_connection_failed(self):
        with patch(
            "app.connectors.sources.clickhouse.clickhouse_connect.get_async_client",
            AsyncMock(
                side_effect=OperationalError("Network Error: Connection timeout")
            ),
        ):
            connector = make_connector(host="unreachable.invalid")
            with pytest.raises(ConnectionFailedError, match="unreachable.invalid"):
                await connector.connect()

    @pytest.mark.asyncio
    async def test_authentication_failure_raises_connection_failed(self):
        with patch(
            "app.connectors.sources.clickhouse.clickhouse_connect.get_async_client",
            AsyncMock(
                side_effect=DatabaseError(
                    "Authentication failed (AUTHENTICATION_FAILED)"
                )
            ),
        ):
            connector = make_connector(username="etl_user")
            with pytest.raises(ConnectionFailedError):
                await connector.connect()

    @pytest.mark.asyncio
    async def test_generic_clickhouse_error_raises_connection_failed(self):
        with patch(
            "app.connectors.sources.clickhouse.clickhouse_connect.get_async_client",
            AsyncMock(side_effect=Error("something else broke")),
        ):
            connector = make_connector()
            with pytest.raises(ConnectionFailedError):
                await connector.connect()


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_closes_the_client(self, mock_get_async_client):
        _, client = mock_get_async_client
        connector = make_connector()
        await connector.connect()

        await connector.disconnect()

        client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_is_a_noop_when_never_connected(self):
        connector = make_connector()
        await connector.disconnect()  # must not raise

    @pytest.mark.asyncio
    async def test_context_manager_connects_and_disconnects(
        self, mock_get_async_client
    ):
        get_async_client, client = mock_get_async_client
        connector = make_connector()

        async with connector as ctx:
            assert ctx is connector
            get_async_client.assert_awaited_once()

        client.close.assert_awaited_once()


class TestTestConnection:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self, mock_get_async_client):
        connector = make_connector()
        assert await connector.test_connection() is True

    @pytest.mark.asyncio
    async def test_closes_client_it_opened_for_itself(self, mock_get_async_client):
        connector = make_connector()
        await connector.test_connection()
        assert connector._client is None

    @pytest.mark.asyncio
    async def test_leaves_an_already_open_client_connected(self, mock_get_async_client):
        connector = make_connector()
        await connector.connect()

        await connector.test_connection()

        assert connector._client is not None

    @pytest.mark.asyncio
    async def test_query_failure_raises_connection_failed(self, mock_get_async_client):
        _, client = mock_get_async_client
        client.ping = AsyncMock(side_effect=Error("boom"))
        connector = make_connector()

        with pytest.raises(ConnectionFailedError):
            await connector.test_connection()


class TestGetTables:
    @pytest.mark.asyncio
    async def test_requires_an_active_connection(self):
        connector = make_connector()
        with pytest.raises(NotConnectedError):
            await connector.get_tables()

    @pytest.mark.asyncio
    async def test_maps_rows_to_table_info(self, mock_get_async_client):
        _, client = mock_get_async_client
        client.query = AsyncMock(
            return_value=make_query_result(
                column_names=("database", "name", "engine"),
                result_rows=[
                    ("analytics", "contacts", "MergeTree"),
                    ("analytics", "contacts_view", "View"),
                ],
            )
        )
        connector = make_connector()
        await connector.connect()

        tables = await connector.get_tables()

        assert tables == [
            TableInfo(name="contacts", schema="analytics", kind="table"),
            TableInfo(name="contacts_view", schema="analytics", kind="view"),
        ]


class TestGetTableSchema:
    @pytest.mark.asyncio
    async def test_maps_rows_to_column_schema(self, mock_get_async_client):
        _, client = mock_get_async_client
        client.query = AsyncMock(
            return_value=make_query_result(
                column_names=("name", "type", "is_in_primary_key"),
                result_rows=[
                    ("id", "UInt32", 1),
                    ("email", "Nullable(String)", 0),
                ],
            )
        )
        connector = make_connector()
        await connector.connect()

        columns = await connector.get_table_schema("contacts", schema="analytics")

        assert columns == [
            ColumnSchema(
                name="id", data_type="UInt32", nullable=False, is_primary_key=True
            ),
            ColumnSchema(
                name="email",
                data_type="Nullable(String)",
                nullable=True,
                is_primary_key=False,
            ),
        ]

    @pytest.mark.asyncio
    async def test_passes_schema_and_table_name_as_query_parameters(
        self, mock_get_async_client
    ):
        _, client = mock_get_async_client
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError):
            await connector.get_table_schema("ghost_table", schema="reporting")

        _, kwargs = client.query.call_args
        assert kwargs["parameters"] == {"db": "reporting", "t": "ghost_table"}

    @pytest.mark.asyncio
    async def test_raises_table_not_found_when_no_columns_returned(
        self, mock_get_async_client
    ):
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError, match="ghost_table"):
            await connector.get_table_schema("ghost_table")

    @pytest.mark.asyncio
    async def test_defaults_to_connector_database(self, mock_get_async_client):
        _, client = mock_get_async_client
        connector = make_connector(database="analytics")
        await connector.connect()

        with pytest.raises(TableNotFoundError):
            await connector.get_table_schema("contacts")

        _, kwargs = client.query.call_args
        assert kwargs["parameters"] == {"db": "analytics", "t": "contacts"}


class TestFetchData:
    @pytest.mark.asyncio
    async def test_requires_an_active_connection(self):
        connector = make_connector()
        with pytest.raises(NotConnectedError):
            await connector.fetch_data("contacts")

    @pytest.mark.asyncio
    async def test_selects_all_columns_by_default(self, mock_get_async_client):
        _, client = mock_get_async_client
        connector = make_connector(database="analytics")
        await connector.connect()

        await connector.fetch_data("contacts")

        sql = client.query.call_args.args[0]
        assert sql == "SELECT * FROM `analytics`.`contacts`"

    @pytest.mark.asyncio
    async def test_selects_requested_columns_quoted(self, mock_get_async_client):
        _, client = mock_get_async_client
        connector = make_connector()
        await connector.connect()

        await connector.fetch_data("contacts", columns=["id", "email"], schema="crm")

        sql = client.query.call_args.args[0]
        assert sql == "SELECT `id`, `email` FROM `crm`.`contacts`"

    @pytest.mark.asyncio
    async def test_appends_where_clause_verbatim(self, mock_get_async_client):
        _, client = mock_get_async_client
        connector = make_connector()
        await connector.connect()

        await connector.fetch_data("contacts", where="updated_at > yesterday()")

        sql = client.query.call_args.args[0]
        assert "WHERE updated_at > yesterday()" in sql

    @pytest.mark.asyncio
    async def test_appends_limit(self, mock_get_async_client):
        _, client = mock_get_async_client
        connector = make_connector()
        await connector.connect()

        await connector.fetch_data("contacts", limit=50)

        sql = client.query.call_args.args[0]
        assert sql.endswith("LIMIT 50")

    @pytest.mark.asyncio
    async def test_returns_rows_as_plain_dicts(self, mock_get_async_client):
        _, client = mock_get_async_client
        client.query = AsyncMock(
            return_value=make_query_result(
                column_names=("id", "email"),
                result_rows=[(1, "a@example.com")],
            )
        )
        connector = make_connector()
        await connector.connect()

        rows = await connector.fetch_data("contacts")

        assert rows == [{"id": 1, "email": "a@example.com"}]
        assert isinstance(rows[0], dict)

    @pytest.mark.asyncio
    async def test_rejects_invalid_table_identifier(self, mock_get_async_client):
        connector = make_connector()
        await connector.connect()

        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            await connector.fetch_data("contacts; DROP TABLE users")

    @pytest.mark.asyncio
    async def test_rejects_invalid_column_identifier(self, mock_get_async_client):
        connector = make_connector()
        await connector.connect()

        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            await connector.fetch_data("contacts", columns=["email; DROP TABLE users"])

    @pytest.mark.asyncio
    async def test_unknown_table_raises_table_not_found(self, mock_get_async_client):
        _, client = mock_get_async_client
        client.query = AsyncMock(
            side_effect=DatabaseError(
                "Code: 60. DB::Exception: Unknown table (UNKNOWN_TABLE)"
            )
        )
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError):
            await connector.fetch_data("ghost_table")

    @pytest.mark.asyncio
    async def test_other_query_errors_are_not_swallowed(self, mock_get_async_client):
        _, client = mock_get_async_client
        client.query = AsyncMock(
            side_effect=DatabaseError("Code: 999. Some other issue")
        )
        connector = make_connector()
        await connector.connect()

        with pytest.raises(DatabaseError):
            await connector.fetch_data("contacts")


class TestQuoteIdentifier:
    @pytest.mark.parametrize("identifier", ["events", "_private", "col_1", "A"])
    def test_accepts_valid_identifiers(self, identifier):
        assert _quote_identifier(identifier) == f"`{identifier}`"

    @pytest.mark.parametrize(
        "identifier",
        ["events; DROP TABLE x", "events`--", "events events", "1events", ""],
    )
    def test_rejects_invalid_identifiers(self, identifier):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _quote_identifier(identifier)
