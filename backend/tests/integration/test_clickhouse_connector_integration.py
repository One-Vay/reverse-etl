"""Integration tests for ClickHouseConnector against a real ClickHouse instance.

Requires Docker. These are marked `integration` and excluded from the
default `pytest` run (see `[tool.pytest.ini_options]` in pyproject.toml).
Run them explicitly with:

    pytest tests/integration -m integration -v

The container is started once per module and shared across tests for
speed; each test only reads, so there's no cross-test interference.
"""

import clickhouse_connect
import pytest
import pytest_asyncio
from testcontainers.community.clickhouse import ClickHouseContainer

from app.connectors.base import ConnectionFailedError, TableNotFoundError
from app.connectors.sources.clickhouse import ClickHouseConnector

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def ch_container():
    with ClickHouseContainer("clickhouse/clickhouse-server:24-alpine") as container:
        yield container


@pytest.fixture(scope="module")
def ch_connection_params(ch_container: ClickHouseContainer) -> dict[str, object]:
    return {
        "host": ch_container.get_container_host_ip(),
        "port": int(ch_container.get_exposed_port(8123)),
        "database": ch_container.dbname,
        "username": ch_container.username,
        "password": ch_container.password,
    }


@pytest_asyncio.fixture(scope="module")
async def seeded_database(ch_connection_params: dict) -> dict:
    """Create a table + view with known data, via a raw client kept
    separate from the connector under test."""
    client = await clickhouse_connect.get_async_client(
        host=ch_connection_params["host"],
        port=ch_connection_params["port"],
        username=ch_connection_params["username"],
        password=ch_connection_params["password"],
        database=ch_connection_params["database"],
    )
    try:
        await client.command(
            "CREATE TABLE contacts ("
            "id UInt32, email String, full_name Nullable(String), "
            "is_active UInt8"
            ") ENGINE = MergeTree ORDER BY id"
        )
        await client.command(
            "INSERT INTO contacts (id, email, full_name, is_active) VALUES "
            "(1, 'a@example.com', 'Alice', 1), (2, 'b@example.com', 'Bob', 0)"
        )
        await client.command(
            "CREATE VIEW active_contacts AS SELECT * FROM contacts WHERE is_active = 1"
        )
    finally:
        await client.close()
    return ch_connection_params


@pytest_asyncio.fixture
async def connector(seeded_database: dict):
    conn = ClickHouseConnector(**seeded_database)
    async with conn:
        yield conn


class TestConnection:
    @pytest.mark.asyncio
    async def test_test_connection_succeeds_with_valid_credentials(self, connector):
        assert await connector.test_connection() is True

    @pytest.mark.asyncio
    async def test_test_connection_fails_with_wrong_password(
        self, seeded_database: dict
    ):
        bad_connector = ClickHouseConnector(**{**seeded_database, "password": "wrong"})
        with pytest.raises(ConnectionFailedError):
            await bad_connector.test_connection()

    @pytest.mark.asyncio
    async def test_connect_fails_against_unreachable_host(self, seeded_database: dict):
        bad_connector = ClickHouseConnector(
            **{**seeded_database, "host": "127.0.0.1", "port": 1, "connect_timeout": 2}
        )
        with pytest.raises(ConnectionFailedError):
            await bad_connector.connect()


class TestGetTables:
    @pytest.mark.asyncio
    async def test_lists_the_seeded_table_and_view(self, connector):
        tables = await connector.get_tables()
        found = {(t.schema, t.name, t.kind) for t in tables}
        assert (connector._database, "contacts", "table") in found
        assert (connector._database, "active_contacts", "view") in found


class TestGetTableSchema:
    @pytest.mark.asyncio
    async def test_describes_columns_and_primary_key(self, connector):
        columns = await connector.get_table_schema("contacts")
        by_name = {c.name: c for c in columns}

        assert by_name["id"].is_primary_key is True
        assert by_name["id"].nullable is False
        assert by_name["email"].nullable is False
        assert by_name["full_name"].nullable is True
        assert by_name["full_name"].is_primary_key is False

    @pytest.mark.asyncio
    async def test_raises_for_a_table_that_does_not_exist(self, connector):
        with pytest.raises(TableNotFoundError):
            await connector.get_table_schema("no_such_table")


class TestFetchData:
    @pytest.mark.asyncio
    async def test_returns_every_row_by_default(self, connector):
        rows = await connector.fetch_data("contacts")
        assert {row["email"] for row in rows} == {"a@example.com", "b@example.com"}

    @pytest.mark.asyncio
    async def test_respects_requested_columns(self, connector):
        rows = await connector.fetch_data("contacts", columns=["email"])
        assert all(list(row.keys()) == ["email"] for row in rows)

    @pytest.mark.asyncio
    async def test_respects_limit(self, connector):
        rows = await connector.fetch_data("contacts", limit=1)
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_respects_where_clause(self, connector):
        rows = await connector.fetch_data("contacts", where="is_active = 1")
        assert [row["email"] for row in rows] == ["a@example.com"]

    @pytest.mark.asyncio
    async def test_reads_from_a_view(self, connector):
        rows = await connector.fetch_data("active_contacts")
        assert [row["email"] for row in rows] == ["a@example.com"]

    @pytest.mark.asyncio
    async def test_raises_for_a_table_that_does_not_exist(self, connector):
        with pytest.raises(TableNotFoundError):
            await connector.fetch_data("no_such_table")
