"""ClickHouse source connector — not implemented yet.

`SourceType.CLICKHOUSE` is already a selectable option when creating a
source (see `app.features.sources.models`), so the factory needs a
connector registered for it. This placeholder keeps that registration
honest: every method fails fast with a clear message instead of the type
silently resolving to nothing, or the app pretending ClickHouse works.

To implement: swap the body of each method for a real implementation
(e.g. using `clickhouse-connect` or `aiochclient`), following the same
shape as `app.connectors.sources.postgres.PostgresConnector`.
"""

from __future__ import annotations

from typing import Any

from app.connectors.base import ColumnSchema, SourceConnector, TableInfo

_NOT_IMPLEMENTED = "The ClickHouse connector is not implemented yet."


class ClickHouseConnector(SourceConnector):
    """Placeholder connector for ClickHouse sources."""

    def __init__(self, **_connection_params: Any) -> None:
        # Connection params are accepted (and ignored) so ConnectorFactory
        # can construct this the same way it constructs a real connector.
        pass

    async def connect(self) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def disconnect(self) -> None:
        return None

    async def test_connection(self) -> bool:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def get_tables(self) -> list[TableInfo]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def get_table_schema(
        self, table_name: str, schema: str | None = None
    ) -> list[ColumnSchema]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def fetch_data(
        self,
        table_name: str,
        columns: list[str] | None = None,
        schema: str | None = None,
        limit: int | None = None,
        where: str | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError(_NOT_IMPLEMENTED)
