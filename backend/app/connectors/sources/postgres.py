"""PostgreSQL source connector, backed by an `asyncpg` connection pool."""

from __future__ import annotations

import re
from typing import Any

import asyncpg

from app.connectors.base import (
    ColumnSchema,
    ConnectionFailedError,
    NotConnectedError,
    SourceConnector,
    TableInfo,
    TableNotFoundError,
)

# Matches a valid, unquoted PostgreSQL identifier. asyncpg has no API for
# safely quoting identifiers (only for binding *values*), so table/schema/
# column names are validated against this allow-list before being
# interpolated into SQL — rejecting anything containing quotes, semicolons,
# whitespace, etc. It's the standard mitigation for the fact that SQL has
# no parameter-binding syntax for identifiers.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_DEFAULT_SCHEMA = "public"


def _quote_identifier(identifier: str) -> str:
    """Double-quote a single SQL identifier after validating its charset.

    Raises:
        ValueError: If `identifier` isn't a plain `[A-Za-z_][A-Za-z0-9_]*`
            token — i.e. it contains anything that could break out of a
            quoted identifier or inject additional SQL.
    """
    if not _IDENTIFIER_RE.match(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return f'"{identifier}"'


class PostgresConnector(SourceConnector):
    """Reads schema metadata and rows from a PostgreSQL database.

    Uses a small connection pool (via `asyncpg.create_pool`) rather than a
    single connection so that, once wired into request-serving code,
    concurrent introspection/preview calls don't serialize on one socket.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        min_pool_size: int = 1,
        max_pool_size: int = 5,
        connect_timeout: float = 10.0,
        command_timeout: float = 30.0,
    ) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._username = username
        self._password = password
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._connect_timeout = connect_timeout
        self._command_timeout = command_timeout
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is not None:
            return
        try:
            self._pool = await asyncpg.create_pool(
                host=self._host,
                port=self._port,
                database=self._database,
                user=self._username,
                password=self._password,
                min_size=self._min_pool_size,
                max_size=self._max_pool_size,
                timeout=self._connect_timeout,
                command_timeout=self._command_timeout,
            )
        except asyncpg.InvalidPasswordError as exc:
            raise ConnectionFailedError(
                f"Authentication failed for user '{self._username}'."
            ) from exc
        except asyncpg.InvalidCatalogNameError as exc:
            raise ConnectionFailedError(
                f"Database '{self._database}' does not exist on {self._host}:{self._port}."
            ) from exc
        except (OSError, TimeoutError) as exc:
            raise ConnectionFailedError(
                f"Could not reach PostgreSQL at {self._host}:{self._port}: {exc}"
            ) from exc
        except asyncpg.PostgresError as exc:
            raise ConnectionFailedError(
                f"Failed to connect to PostgreSQL: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def test_connection(self) -> bool:
        was_connected = self._pool is not None
        if not was_connected:
            await self.connect()
        try:
            assert self._pool is not None
            result = await self._pool.fetchval("SELECT 1")
            return result == 1
        except asyncpg.PostgresError as exc:
            raise ConnectionFailedError(f"Connection test failed: {exc}") from exc
        finally:
            if not was_connected:
                await self.disconnect()

    async def get_tables(self) -> list[TableInfo]:
        pool = self._require_pool()
        rows = await pool.fetch(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
            ORDER BY table_schema, table_name
            """
        )
        return [
            TableInfo(
                name=row["table_name"],
                schema=row["table_schema"],
                kind="view" if row["table_type"] == "VIEW" else "table",
            )
            for row in rows
        ]

    async def get_table_schema(
        self, table_name: str, schema: str | None = None
    ) -> list[ColumnSchema]:
        pool = self._require_pool()
        schema = schema or _DEFAULT_SCHEMA

        rows = await pool.fetch(
            """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable = 'YES' AS nullable,
                pk.column_name IS NOT NULL AS is_primary_key
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = $1
                    AND tc.table_name = $2
            ) pk ON pk.column_name = c.column_name
            WHERE c.table_schema = $1 AND c.table_name = $2
            ORDER BY c.ordinal_position
            """,
            schema,
            table_name,
        )
        if not rows:
            raise TableNotFoundError(f"Table '{schema}.{table_name}' does not exist.")

        return [
            ColumnSchema(
                name=row["column_name"],
                data_type=row["data_type"],
                nullable=row["nullable"],
                is_primary_key=row["is_primary_key"],
            )
            for row in rows
        ]

    async def fetch_data(
        self,
        table_name: str,
        columns: list[str] | None = None,
        schema: str | None = None,
        limit: int | None = None,
        where: str | None = None,
    ) -> list[dict[str, Any]]:
        pool = self._require_pool()
        schema = schema or _DEFAULT_SCHEMA

        select_clause = (
            ", ".join(_quote_identifier(column) for column in columns)
            if columns
            else "*"
        )
        qualified_table = f"{_quote_identifier(schema)}.{_quote_identifier(table_name)}"

        sql = f"SELECT {select_clause} FROM {qualified_table}"  # noqa: S608 — identifiers validated above
        if where:
            sql += f" WHERE {where}"

        params: list[Any] = []
        if limit is not None:
            params.append(limit)
            sql += f" LIMIT ${len(params)}"

        try:
            rows = await pool.fetch(sql, *params)
        except asyncpg.UndefinedTableError as exc:
            raise TableNotFoundError(
                f"Table '{schema}.{table_name}' does not exist."
            ) from exc

        return [dict(row) for row in rows]

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise NotConnectedError(
                "Connector is not connected — call connect() first, or use "
                "'async with connector:'."
            )
        return self._pool
