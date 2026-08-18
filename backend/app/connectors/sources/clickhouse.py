"""ClickHouse source connector, backed by `clickhouse-connect`'s async client."""

from __future__ import annotations

import re
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.exceptions import Error, OperationalError

from app.connectors.base import (
    ColumnSchema,
    ConnectionFailedError,
    NotConnectedError,
    SourceConnector,
    TableInfo,
    TableNotFoundError,
)

# Matches a valid, unquoted ClickHouse identifier. Same rationale as the
# Postgres connector's allow-list: there's no driver API for safely quoting
# identifiers, only for binding *values*, so table/database/column names are
# validated before being interpolated into SQL.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_DEFAULT_DATABASE = "default"


def _quote_identifier(identifier: str) -> str:
    """Backtick-quote a single SQL identifier after validating its charset.

    Raises:
        ValueError: If `identifier` isn't a plain `[A-Za-z_][A-Za-z0-9_]*`
            token — i.e. it contains anything that could break out of a
            quoted identifier or inject additional SQL.
    """
    if not _IDENTIFIER_RE.match(identifier):
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return f"`{identifier}`"


class ClickHouseConnector(SourceConnector):
    """Reads schema metadata and rows from a ClickHouse database.

    Uses `clickhouse_connect`'s async HTTP client, talking to ClickHouse's
    HTTP interface (default port 8123) rather than its native TCP protocol.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int = 8123,
        database: str = _DEFAULT_DATABASE,
        username: str = "default",
        password: str = "",
        connect_timeout: float = 10.0,
    ) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._username = username
        self._password = password
        self._connect_timeout = connect_timeout
        self._client: AsyncClient | None = None

    async def connect(self) -> None:
        if self._client is not None:
            return
        try:
            self._client = await clickhouse_connect.get_async_client(
                host=self._host,
                port=self._port,
                username=self._username,
                password=self._password,
                database=self._database,
                connect_timeout=self._connect_timeout,
            )
        except OperationalError as exc:
            raise ConnectionFailedError(
                f"Could not reach ClickHouse at {self._host}:{self._port}: {exc}"
            ) from exc
        except Error as exc:
            raise ConnectionFailedError(
                f"Failed to connect to ClickHouse: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def test_connection(self) -> bool:
        was_connected = self._client is not None
        if not was_connected:
            await self.connect()
        try:
            assert self._client is not None
            return await self._client.ping()
        except Error as exc:
            raise ConnectionFailedError(f"Connection test failed: {exc}") from exc
        finally:
            if not was_connected:
                await self.disconnect()

    async def get_tables(self) -> list[TableInfo]:
        client = self._require_client()
        result = await client.query(
            "SELECT database, name, engine FROM system.tables "
            "WHERE database = %(db)s ORDER BY name",
            parameters={"db": self._database},
        )
        return [
            TableInfo(
                name=name,
                schema=database,
                kind="view" if "View" in engine else "table",
            )
            for database, name, engine in result.result_rows
        ]

    async def get_table_schema(
        self, table_name: str, schema: str | None = None
    ) -> list[ColumnSchema]:
        client = self._require_client()
        schema = schema or self._database

        result = await client.query(
            "SELECT name, type, is_in_primary_key FROM system.columns "
            "WHERE database = %(db)s AND table = %(t)s ORDER BY position",
            parameters={"db": schema, "t": table_name},
        )
        if not result.result_rows:
            raise TableNotFoundError(f"Table '{schema}.{table_name}' does not exist.")

        return [
            ColumnSchema(
                name=name,
                data_type=data_type,
                nullable=data_type.startswith("Nullable("),
                is_primary_key=bool(is_in_primary_key),
            )
            for name, data_type, is_in_primary_key in result.result_rows
        ]

    async def fetch_data(
        self,
        table_name: str,
        columns: list[str] | None = None,
        schema: str | None = None,
        limit: int | None = None,
        where: str | None = None,
    ) -> list[dict[str, Any]]:
        client = self._require_client()
        schema = schema or self._database

        select_clause = (
            ", ".join(_quote_identifier(column) for column in columns)
            if columns
            else "*"
        )
        qualified_table = f"{_quote_identifier(schema)}.{_quote_identifier(table_name)}"

        sql = f"SELECT {select_clause} FROM {qualified_table}"  # noqa: S608 — identifiers validated above
        if where:
            sql += f" WHERE {where}"
        if limit is not None:
            sql += f" LIMIT {int(limit)}"

        try:
            result = await client.query(sql)
        except Error as exc:
            if "UNKNOWN_TABLE" in str(exc):
                raise TableNotFoundError(
                    f"Table '{schema}.{table_name}' does not exist."
                ) from exc
            raise

        columns_returned = result.column_names
        return [
            dict(zip(columns_returned, row, strict=True)) for row in result.result_rows
        ]

    def _require_client(self) -> AsyncClient:
        if self._client is None:
            raise NotConnectedError(
                "Connector is not connected — call connect() first, or use "
                "'async with connector:'."
            )
        return self._client
