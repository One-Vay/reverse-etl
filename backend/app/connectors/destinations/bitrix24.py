"""Bitrix24 destination connector, backed by an incoming-webhook REST client.

Bitrix24's simplest integration mechanism is an "incoming webhook": a
portal admin creates one and gets a base URL of the form
`https://mycompany.bitrix24.ru/rest/1/xxxxxxxxxxxxxxxx/`, where `1` is the
acting user's ID and `xxxxxxxxxxxxxxxx` is the webhook's secret code. That
URL splits naturally along this connector's two stored credentials:

- `api_url`  — the portal's base URL, e.g. `https://mycompany.bitrix24.ru`
  (not secret, safe to display in the UI).
- `auth_token` — the webhook path segment `{user_id}/{webhook_code}`, e.g.
  `1/xxxxxxxxxxxxxxxx` (secret, stored encrypted).

A REST method is then called as
`{api_url}/rest/{auth_token}/{method}`, e.g.
`https://mycompany.bitrix24.ru/rest/1/xxxxxxxxxxxxxxxx/crm.lead.add`.

Only the four standard CRM entities are exposed — Bitrix24 also supports
custom "SPA" entity types, but discovering those requires additional REST
calls (`crm.type.list`) beyond this connector's current scope.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.connectors.base import (
    ColumnSchema,
    ConnectionFailedError,
    DestinationConnector,
    NotConnectedError,
    TableNotFoundError,
)
from app.connectors.destinations._http import request_json

_SYSTEM_NAME = "Bitrix24"

# Standard Bitrix24 CRM entity types this connector supports, mapped to the
# singular noun used in their REST method names (`crm.{entity}.add`, ...).
_ENTITIES = ("lead", "contact", "company", "deal")

# Field codes Bitrix24 exposes as `crm_multifield` — the API expects a list
# of `{"VALUE": ..., "VALUE_TYPE": ...}` objects rather than a scalar, and
# silently drops a plain string/number with no error. Callers of
# `upsert_data` (e.g. a mapping's field transformations) naturally produce
# plain scalar values, so those are auto-wrapped here — this is a quirk of
# Bitrix24's API shape, not something a caller should need to know about.
_MULTIFIELD_CODES = frozenset({"PHONE", "EMAIL", "WEB", "IM", "LINK"})
_DEFAULT_MULTIFIELD_VALUE_TYPE = "WORK"


def _to_bitrix_field_value(field_code: str, value: Any) -> Any:
    if field_code not in _MULTIFIELD_CODES or value is None:
        return value
    if isinstance(value, list):
        return value
    return [{"VALUE": value, "VALUE_TYPE": _DEFAULT_MULTIFIELD_VALUE_TYPE}]


class Bitrix24Connector(DestinationConnector):
    """Reads entity metadata from, and writes records to, a Bitrix24 CRM
    via its REST API, authenticated with an incoming webhook."""

    def __init__(
        self,
        *,
        api_url: str,
        auth_token: str,
        request_timeout: float = 30.0,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._auth_token = auth_token.strip("/")
        self._request_timeout = request_timeout
        self._client: httpx.AsyncClient | None = None

    async def connect(self) -> None:
        if self._client is not None:
            return
        client = httpx.AsyncClient(
            base_url=f"{self._api_url}/rest/{self._auth_token}/",
            timeout=self._request_timeout,
        )
        try:
            await self._call(client, "profile")
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
            await self._call(self._client, "profile")
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

        result = await self._call(client, f"crm.{entity}.fields")
        return [
            ColumnSchema(
                name=field_name,
                data_type=str(field_info.get("type", "string")),
                nullable=field_info.get("isRequired") != "Y",
                is_primary_key=field_name == "ID",
            )
            for field_name, field_info in result.items()
        ]

    async def upsert_data(self, entity: str, records: list[dict[str, Any]]) -> int:
        client = self._require_client()
        self._require_known_entity(entity)

        written = 0
        for record in records:
            record_id = record.get("ID") or record.get("id")
            fields = {
                k: _to_bitrix_field_value(k, v)
                for k, v in record.items()
                if k.upper() != "ID"
            }
            if record_id is not None:
                payload: dict[str, Any] = {"id": record_id, "fields": fields}
                method = f"crm.{entity}.update"
            else:
                payload = {"fields": fields}
                method = f"crm.{entity}.add"

            try:
                await self._call(client, method, json=payload)
            except TableNotFoundError:
                continue
            written += 1

        return written

    async def _call(self, client: httpx.AsyncClient, method: str, **kwargs: Any) -> Any:
        """POST to a Bitrix24 REST method and unwrap its `result` envelope.

        Bitrix24 sometimes reports application-level failures as HTTP 200
        with an `{"error": ..., "error_description": ...}` body instead of
        a non-2xx status, so that shape is checked explicitly in addition
        to `request_json`'s HTTP-status-based mapping.
        """
        body = await request_json(
            client, "POST", method, system_name=_SYSTEM_NAME, **kwargs
        )
        if isinstance(body, dict) and "error" in body:
            description = body.get("error_description", body["error"])
            if body["error"] in ("ERROR_METHOD_NOT_FOUND", "NOT_FOUND"):
                raise TableNotFoundError(f"{_SYSTEM_NAME}: {description}")
            raise ConnectionFailedError(f"{_SYSTEM_NAME} error: {description}")
        return body.get("result") if isinstance(body, dict) else body

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
