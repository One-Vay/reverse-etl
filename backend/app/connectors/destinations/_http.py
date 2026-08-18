"""Shared HTTP request/error-mapping helpers for REST-based destination
connectors (Bitrix24, AmoCRM).

Both connectors talk to a JSON REST API over `httpx.AsyncClient` and need
the same translation from low-level HTTP failures into the connector
layer's own exception types — this module is the one place that logic
lives, so each connector only has to describe *which* endpoint to call.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.connectors.base import ConnectionFailedError, TableNotFoundError


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    system_name: str,
    not_found_status: tuple[int, ...] = (404,),
    **kwargs: Any,
) -> Any:
    """Send a request against a destination's REST API and return its
    parsed JSON body.

    Args:
        client: The connector's `httpx.AsyncClient`.
        method: HTTP method, e.g. `"GET"`, `"POST"`, `"PATCH"`.
        url: Path or absolute URL, resolved against `client.base_url`.
        system_name: Human-readable system name for error messages, e.g.
            `"Bitrix24"`.
        not_found_status: Status codes that mean "the requested entity
            doesn't exist" rather than a generic failure.
        **kwargs: Forwarded to `client.request` (e.g. `json=`, `params=`).

    Raises:
        ConnectionFailedError: On a network-level failure, an
            authentication/authorization failure (401/403), any other
            non-2xx status not in `not_found_status`, or a non-JSON body.
        TableNotFoundError: If the response status is in `not_found_status`.
    """
    try:
        response = await client.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        raise ConnectionFailedError(f"Could not reach {system_name}: {exc}") from exc

    if response.status_code in not_found_status:
        raise TableNotFoundError(
            f"{system_name} has no entity at '{url}' (HTTP {response.status_code})."
        )
    if response.status_code in (401, 403):
        raise ConnectionFailedError(
            f"{system_name} rejected the configured credentials "
            f"(HTTP {response.status_code})."
        )
    if response.is_error:
        raise ConnectionFailedError(
            f"{system_name} request to '{url}' failed with "
            f"HTTP {response.status_code}: {response.text[:300]}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise ConnectionFailedError(
            f"{system_name} returned a non-JSON response for '{url}'."
        ) from exc
