"""AmoCRM destination connector, backed by its REST API v4.

Authenticated with a long-lived API token (a per-integration Bearer token
AmoCRM issues that doesn't require the full OAuth refresh-token dance),
which maps cleanly onto this connector's two stored credentials:

- `api_url` — the account's base URL, e.g. `https://mycompany.amocrm.ru`
  (not secret, safe to display in the UI).
- `auth_token` — the long-lived API token, sent as `Authorization: Bearer
  {auth_token}` (secret, stored encrypted).

Only the standard entity types are exposed — AmoCRM also supports
custom/catalog entities, which is beyond this connector's current scope.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.connectors.base import (
    ColumnSchema,
    DestinationConnector,
    NotConnectedError,
    TableNotFoundError,
)
from app.connectors.destinations._http import request_json

_SYSTEM_NAME = "AmoCRM"

# Standard AmoCRM entity types this connector supports, mapped to their
# REST resource path (`/api/v4/{entity}`).
_ENTITIES = ("leads", "contacts", "companies", "tasks")

# AmoCRM's fixed, always-present fields per entity. Custom fields (which
# vary per account) are discovered separately via `get_entity_fields`.
_STANDARD_FIELDS: dict[str, list[ColumnSchema]] = {
    "leads": [
        ColumnSchema(
            name="id", data_type="integer", nullable=False, is_primary_key=True
        ),
        ColumnSchema(name="name", data_type="string", nullable=False),
        ColumnSchema(name="price", data_type="integer", nullable=True),
        ColumnSchema(name="status_id", data_type="integer", nullable=True),
        ColumnSchema(name="pipeline_id", data_type="integer", nullable=True),
        ColumnSchema(name="responsible_user_id", data_type="integer", nullable=True),
    ],
    "contacts": [
        ColumnSchema(
            name="id", data_type="integer", nullable=False, is_primary_key=True
        ),
        ColumnSchema(name="name", data_type="string", nullable=False),
        ColumnSchema(name="first_name", data_type="string", nullable=True),
        ColumnSchema(name="last_name", data_type="string", nullable=True),
        ColumnSchema(name="responsible_user_id", data_type="integer", nullable=True),
    ],
    "companies": [
        ColumnSchema(
            name="id", data_type="integer", nullable=False, is_primary_key=True
        ),
        ColumnSchema(name="name", data_type="string", nullable=False),
        ColumnSchema(name="responsible_user_id", data_type="integer", nullable=True),
    ],
    "tasks": [
        ColumnSchema(
            name="id", data_type="integer", nullable=False, is_primary_key=True
        ),
        ColumnSchema(name="text", data_type="string", nullable=False),
        ColumnSchema(name="complete_till", data_type="integer", nullable=True),
        ColumnSchema(name="task_type_id", data_type="integer", nullable=True),
        ColumnSchema(name="responsible_user_id", data_type="integer", nullable=True),
    ],
}

# `tasks` has no custom-fields concept in AmoCRM's API.
_ENTITIES_WITHOUT_CUSTOM_FIELDS = frozenset({"tasks"})


class AmoCRMConnector(DestinationConnector):
    """Reads entity metadata from, and writes records to, an AmoCRM
    account via its REST API v4, authenticated with a long-lived token."""

    def __init__(
        self,
        *,
        api_url: str,
        auth_token: str,
        request_timeout: float = 30.0,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._auth_token = auth_token
        self._request_timeout = request_timeout
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        if self._client is not None:
            return
        client = httpx.AsyncClient(
            base_url=f"{self._api_url}/api/v4/",
            headers={"Authorization": f"Bearer {self._auth_token}"},
            timeout=self._request_timeout,
        )
        try:
            await request_json(client, "GET", "account", system_name=_SYSTEM_NAME)
        except Exception:
            await client.aclose()
            raise
        self._client = client

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def test_connection(self) -> bool:
        was_connected = self._client is not None
        if not was_connected:
            await self.connect()
        try:
            assert self._client is not None
            await request_json(self._client, "GET", "account", system_name=_SYSTEM_NAME)
            return True
        finally:
            if not was_connected:
                await self.disconnect()

    async def get_entities(self) -> list[str]:
        self._require_client()
        return list(_ENTITIES)

    async def get_entity_fields(self, entity: str) -> list[ColumnSchema]:
        client = self._require_client()
        self._require_known_entity(entity)

        fields = list(_STANDARD_FIELDS[entity])
        if entity in _ENTITIES_WITHOUT_CUSTOM_FIELDS:
            return fields

        body = await request_json(
            client, "GET", f"{entity}/custom_fields", system_name=_SYSTEM_NAME
        )
        custom_fields = body.get("_embedded", {}).get("custom_fields", [])
        fields.extend(
            ColumnSchema(
                name=f"custom_fields_values.{field['field_id']}",
                data_type=str(field.get("type", "text")),
                nullable=not field.get("is_required", False),
            )
            for field in custom_fields
        )
        return fields

    async def upsert_data(self, entity: str, records: list[dict[str, Any]]) -> int:
        client = self._require_client()
        self._require_known_entity(entity)

        to_create = [r for r in records if "id" not in r]
        to_update = [r for r in records if "id" in r]

        written = 0
        if to_create:
            body = await request_json(
                client, "POST", entity, system_name=_SYSTEM_NAME, json=to_create
            )
            written += len(body.get("_embedded", {}).get(entity, []))
        if to_update:
            body = await request_json(
                client, "PATCH", entity, system_name=_SYSTEM_NAME, json=to_update
            )
            written += len(body.get("_embedded", {}).get(entity, []))

        return written

    def _require_known_entity(self, entity: str) -> None:
        if entity not in _ENTITIES:
            raise TableNotFoundError(
                f"{_SYSTEM_NAME} has no entity type '{entity}'. "
                f"Available types: {', '.join(_ENTITIES)}."
            )

    def _require_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise NotConnectedError(
                "Connector is not connected — call connect() first, or use "
                "'async with connector:'."
            )
        return self._client
