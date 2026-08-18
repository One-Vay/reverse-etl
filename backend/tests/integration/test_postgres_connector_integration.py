"""Integration tests for PostgresConnector against a real PostgreSQL instance.

Requires Docker. These are marked `integration` and excluded from the
default `pytest` run (see `[tool.pytest.ini_options]` in pyproject.toml).
Run them explicitly with:

    pytest tests/integration -m integration -v

The container is started once per module and shared across tests for
speed; each test only reads, so there's no cross-test interference.
"""

import asyncpg
import pytest
import pytest_asyncio
from testcontainers.community.postgres import PostgresContainer

from app.connectors.base import ConnectionFailedError, TableNotFoundError
from app.connectors.sources.postgres import PostgresConnector

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def pg_container():
    with PostgresContainer("postgres:16-alpine", driver=None) as container:
        yield container


@pytest.fixture(scope="module")
def pg_connection_params(pg_container: PostgresContainer) -> dict[str, object]:
    return {
        "host": pg_container.get_container_host_ip(),
        "port": int(pg_container.get_exposed_port(pg_container.port)),
        "database": pg_container.dbname,
        "username": pg_container.username,
        "password": pg_container.password,
    }


@pytest_asyncio.fixture(scope="module")
async def seeded_database(pg_connection_params: dict) -> dict:
    """Create a table + view with known data, via a raw asyncpg connection
    kept separate from the connector under test."""
    conn = await asyncpg.connect(
        host=pg_connection_params["host"],
        port=pg_connection_params["port"],
        database=pg_connection_params["database"],
        user=pg_connection_params["username"],
        password=pg_connection_params["password"],
    )
    try:
        await conn.execute(
            """
            CREATE TABLE contacts (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                full_name TEXT,
                is_active BOOLEAN NOT NULL DEFAULT true
            )
            """
        )
        await conn.execute(
            """
            INSERT INTO contacts (email, full_name, is_active) VALUES
                ('a@example.com', 'Alice', true),
                ('b@example.com', 'Bob', false)
            """
        )
        await conn.execute(
            "CREATE VIEW active_contacts AS SELECT * FROM contacts WHERE is_active"
        )
    finally:
        await conn.close()
    return pg_connection_params


@pytest_asyncio.fixture
async def connector(seeded_database: dict):
    conn = PostgresConnector(**seeded_database)
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
        bad_connector = PostgresConnector(**{**seeded_database, "password": "wrong"})
        with pytest.raises(ConnectionFailedError):
            await bad_connector.test_connection()

    @pytest.mark.asyncio
    async def test_connect_fails_against_missing_database(self, seeded_database: dict):
        bad_connector = PostgresConnector(
            **{**seeded_database, "database": "does_not_exist"}
        )
        with pytest.raises(ConnectionFailedError):
            await bad_connector.connect()


class TestGetTables:
    @pytest.mark.asyncio
    async def test_lists_the_seeded_table_and_view(self, connector):
        tables = await connector.get_tables()
        found = {(t.schema, t.name, t.kind) for t in tables}
        assert ("public", "contacts", "table") in found
        assert ("public", "active_contacts", "view") in found


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
        rows = await connector.fetch_data("contacts", where="is_active = true")
        assert [row["email"] for row in rows] == ["a@example.com"]

    @pytest.mark.asyncio
    async def test_reads_from_a_view(self, connector):
        rows = await connector.fetch_data("active_contacts")
        assert [row["email"] for row in rows] == ["a@example.com"]

    @pytest.mark.asyncio
    async def test_raises_for_a_table_that_does_not_exist(self, connector):
        with pytest.raises(TableNotFoundError):
            await connector.fetch_data("no_such_table")
