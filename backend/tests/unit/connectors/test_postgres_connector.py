"""Unit tests for PostgresConnector, with asyncpg fully mocked.

These tests never touch a real database — see
tests/integration/test_postgres_connector_integration.py for that.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from app.connectors.base import (
    ColumnSchema,
    ConnectionFailedError,
    NotConnectedError,
    TableInfo,
    TableNotFoundError,
)
from app.connectors.sources.postgres import PostgresConnector, _quote_identifier


def make_connector(**overrides) -> PostgresConnector:
    params = {
        "host": "db.internal",
        "port": 5432,
        "database": "analytics",
        "username": "etl_user",
        "password": "s3cret",
    }
    params.update(overrides)
    return PostgresConnector(**params)


def make_mock_pool() -> MagicMock:
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=[])
    pool.fetchval = AsyncMock(return_value=1)
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def mock_create_pool():
    pool = make_mock_pool()
    with patch(
        "app.connectors.sources.postgres.asyncpg.create_pool",
        AsyncMock(return_value=pool),
    ) as create_pool:
        yield create_pool, pool


class TestConnect:
    @pytest.mark.asyncio
    async def test_connects_with_expected_parameters(self, mock_create_pool):
        create_pool, pool = mock_create_pool
        connector = make_connector(host="db.internal", port=5433, database="analytics")

        await connector.connect()

        create_pool.assert_awaited_once()
        _, kwargs = create_pool.call_args
        assert kwargs["host"] == "db.internal"
        assert kwargs["port"] == 5433
        assert kwargs["database"] == "analytics"
        assert kwargs["user"] == "etl_user"
        assert kwargs["password"] == "s3cret"

    @pytest.mark.asyncio
    async def test_is_idempotent(self, mock_create_pool):
        create_pool, _ = mock_create_pool
        connector = make_connector()

        await connector.connect()
        await connector.connect()

        create_pool.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_password_raises_connection_failed(self):
        with patch(
            "app.connectors.sources.postgres.asyncpg.create_pool",
            AsyncMock(side_effect=asyncpg.InvalidPasswordError("bad password")),
        ):
            connector = make_connector(username="etl_user")
            with pytest.raises(ConnectionFailedError, match="etl_user"):
                await connector.connect()

    @pytest.mark.asyncio
    async def test_invalid_database_raises_connection_failed(self):
        with patch(
            "app.connectors.sources.postgres.asyncpg.create_pool",
            AsyncMock(side_effect=asyncpg.InvalidCatalogNameError("nope")),
        ):
            connector = make_connector(database="ghost_db")
            with pytest.raises(ConnectionFailedError, match="ghost_db"):
                await connector.connect()

    @pytest.mark.asyncio
    async def test_unreachable_host_raises_connection_failed(self):
        with patch(
            "app.connectors.sources.postgres.asyncpg.create_pool",
            AsyncMock(side_effect=OSError("connection refused")),
        ):
            connector = make_connector(host="unreachable.invalid")
            with pytest.raises(ConnectionFailedError, match="unreachable.invalid"):
                await connector.connect()

    @pytest.mark.asyncio
    async def test_generic_postgres_error_raises_connection_failed(self):
        with patch(
            "app.connectors.sources.postgres.asyncpg.create_pool",
            AsyncMock(side_effect=asyncpg.PostgresError("something else broke")),
        ):
            connector = make_connector()
            with pytest.raises(ConnectionFailedError):
                await connector.connect()


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_closes_the_pool(self, mock_create_pool):
        _, pool = mock_create_pool
        connector = make_connector()
        await connector.connect()

        await connector.disconnect()

        pool.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_is_a_noop_when_never_connected(self):
        connector = make_connector()
        await connector.disconnect()  # must not raise

    @pytest.mark.asyncio
    async def test_context_manager_connects_and_disconnects(self, mock_create_pool):
        create_pool, pool = mock_create_pool
        connector = make_connector()

        async with connector as ctx:
            assert ctx is connector
            create_pool.assert_awaited_once()

        pool.close.assert_awaited_once()


class TestTestConnection:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self, mock_create_pool):
        connector = make_connector()
        assert await connector.test_connection() is True

    @pytest.mark.asyncio
    async def test_closes_pool_it_opened_for_itself(self, mock_create_pool):
        connector = make_connector()
        await connector.test_connection()
        assert connector._pool is None

    @pytest.mark.asyncio
    async def test_leaves_an_already_open_pool_connected(self, mock_create_pool):
        connector = make_connector()
        await connector.connect()

        await connector.test_connection()

        assert connector._pool is not None

    @pytest.mark.asyncio
    async def test_query_failure_raises_connection_failed(self, mock_create_pool):
        _, pool = mock_create_pool
        pool.fetchval = AsyncMock(side_effect=asyncpg.PostgresError("boom"))
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
    async def test_maps_rows_to_table_info(self, mock_create_pool):
        _, pool = mock_create_pool
        pool.fetch = AsyncMock(
            return_value=[
                {
                    "table_schema": "public",
                    "table_name": "contacts",
                    "table_type": "BASE TABLE",
                },
                {
                    "table_schema": "public",
                    "table_name": "contacts_view",
                    "table_type": "VIEW",
                },
            ]
        )
        connector = make_connector()
        await connector.connect()

        tables = await connector.get_tables()

        assert tables == [
            TableInfo(name="contacts", schema="public", kind="table"),
            TableInfo(name="contacts_view", schema="public", kind="view"),
        ]


class TestGetTableSchema:
    @pytest.mark.asyncio
    async def test_maps_rows_to_column_schema(self, mock_create_pool):
        _, pool = mock_create_pool
        pool.fetch = AsyncMock(
            return_value=[
                {
                    "column_name": "id",
                    "data_type": "integer",
                    "nullable": False,
                    "is_primary_key": True,
                },
                {
                    "column_name": "email",
                    "data_type": "character varying",
                    "nullable": True,
                    "is_primary_key": False,
                },
            ]
        )
        connector = make_connector()
        await connector.connect()

        columns = await connector.get_table_schema("contacts", schema="public")

        assert columns == [
            ColumnSchema(
                name="id", data_type="integer", nullable=False, is_primary_key=True
            ),
            ColumnSchema(
                name="email",
                data_type="character varying",
                nullable=True,
                is_primary_key=False,
            ),
        ]

    @pytest.mark.asyncio
    async def test_passes_schema_and_table_name_as_query_parameters(
        self, mock_create_pool
    ):
        _, pool = mock_create_pool
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError):
            await connector.get_table_schema("ghost_table", schema="reporting")

        _, *params = pool.fetch.call_args.args
        assert params == ["reporting", "ghost_table"]

    @pytest.mark.asyncio
    async def test_raises_table_not_found_when_no_columns_returned(
        self, mock_create_pool
    ):
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError, match="ghost_table"):
            await connector.get_table_schema("ghost_table")

    @pytest.mark.asyncio
    async def test_defaults_to_public_schema(self, mock_create_pool):
        _, pool = mock_create_pool
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError):
            await connector.get_table_schema("contacts")

        _, schema_arg, table_arg = pool.fetch.call_args.args
        assert schema_arg == "public"
        assert table_arg == "contacts"


class TestFetchData:
    @pytest.mark.asyncio
    async def test_requires_an_active_connection(self):
        connector = make_connector()
        with pytest.raises(NotConnectedError):
            await connector.fetch_data("contacts")

    @pytest.mark.asyncio
    async def test_selects_all_columns_by_default(self, mock_create_pool):
        _, pool = mock_create_pool
        connector = make_connector()
        await connector.connect()

        await connector.fetch_data("contacts")

        sql = pool.fetch.call_args.args[0]
        assert sql == 'SELECT * FROM "public"."contacts"'

    @pytest.mark.asyncio
    async def test_selects_requested_columns_quoted(self, mock_create_pool):
        _, pool = mock_create_pool
        connector = make_connector()
        await connector.connect()

        await connector.fetch_data("contacts", columns=["id", "email"], schema="crm")

        sql = pool.fetch.call_args.args[0]
        assert sql == 'SELECT "id", "email" FROM "crm"."contacts"'

    @pytest.mark.asyncio
    async def test_appends_where_clause_verbatim(self, mock_create_pool):
        _, pool = mock_create_pool
        connector = make_connector()
        await connector.connect()

        await connector.fetch_data(
            "contacts", where="updated_at > now() - interval '1 day'"
        )

        sql = pool.fetch.call_args.args[0]
        assert "WHERE updated_at > now() - interval '1 day'" in sql

    @pytest.mark.asyncio
    async def test_binds_limit_as_a_parameter_not_interpolated(self, mock_create_pool):
        _, pool = mock_create_pool
        connector = make_connector()
        await connector.connect()

        await connector.fetch_data("contacts", limit=50)

        sql, *params = pool.fetch.call_args.args
        assert sql.endswith("LIMIT $1")
        assert params == [50]

    @pytest.mark.asyncio
    async def test_returns_rows_as_plain_dicts(self, mock_create_pool):
        _, pool = mock_create_pool
        pool.fetch = AsyncMock(return_value=[{"id": 1, "email": "a@example.com"}])
        connector = make_connector()
        await connector.connect()

        rows = await connector.fetch_data("contacts")

        assert rows == [{"id": 1, "email": "a@example.com"}]
        assert isinstance(rows[0], dict)

    @pytest.mark.asyncio
    async def test_rejects_invalid_table_identifier(self, mock_create_pool):
        connector = make_connector()
        await connector.connect()

        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            await connector.fetch_data("contacts; DROP TABLE users")

    @pytest.mark.asyncio
    async def test_rejects_invalid_column_identifier(self, mock_create_pool):
        connector = make_connector()
        await connector.connect()

        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            await connector.fetch_data("contacts", columns=["email; DROP TABLE users"])

    @pytest.mark.asyncio
    async def test_undefined_table_raises_table_not_found(self, mock_create_pool):
        _, pool = mock_create_pool
        pool.fetch = AsyncMock(side_effect=asyncpg.UndefinedTableError("missing"))
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError):
            await connector.fetch_data("ghost_table")


class TestQuoteIdentifier:
    @pytest.mark.parametrize("identifier", ["users", "_private", "col_1", "A"])
    def test_accepts_valid_identifiers(self, identifier):
        assert _quote_identifier(identifier) == f'"{identifier}"'

    @pytest.mark.parametrize(
        "identifier",
        ["users; DROP TABLE x", 'users"--', "users users", "1users", ""],
    )
    def test_rejects_invalid_identifiers(self, identifier):
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            _quote_identifier(identifier)
