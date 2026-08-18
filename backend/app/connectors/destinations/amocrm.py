"""AmoCRM destination connector — not implemented yet.

`DestinationType.AMOCRM` is already selectable when creating a
destination (see `app.features.destinations.models`), so the factory
needs a connector registered for it. This placeholder keeps that
registration honest — see `app.connectors.sources.clickhouse` for the
rationale.

To implement: swap the body of each method for real AmoCRM REST API
calls (OAuth), following the same shape as
`app.connectors.sources.postgres.PostgresConnector`.
"""

from __future__ import annotations

from typing import Any

from app.connectors.base import ColumnSchema, DestinationConnector

_NOT_IMPLEMENTED = "The AmoCRM connector is not implemented yet."


class AmoCRMConnector(DestinationConnector):
    """Placeholder connector for AmoCRM destinations."""

    def __init__(self, **_connection_params: Any) -> None:
        pass

    async def connect(self) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def disconnect(self) -> None:
        return None

    async def test_connection(self) -> bool:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def get_entities(self) -> list[str]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def get_entity_fields(self, entity: str) -> list[ColumnSchema]:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    async def upsert_data(self, entity: str, records: list[dict[str, Any]]) -> int:
        raise NotImplementedError(_NOT_IMPLEMENTED)
