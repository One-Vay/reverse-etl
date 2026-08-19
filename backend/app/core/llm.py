"""Thin client for a local Ollama server, used for AI-suggested field
mappings (see `app.features.mappings.suggest`). Deliberately not a
general-purpose LLM abstraction — this app has exactly one AI feature,
and Ollama's HTTP API is simple enough not to need a vendored SDK on top
of the `httpx` this project already depends on.
"""

from __future__ import annotations

import json
from typing import Any

import httpx


class LLMUnavailableError(Exception):
    """Raised when Ollama can't be reached or returns an unusable response.
    Callers are expected to degrade gracefully (e.g. return no suggestions)
    rather than let this fail the request — AI suggestions are optional."""


async def generate_json(
    prompt: str, *, model: str, base_url: str, timeout: float = 60.0
) -> Any:
    """Ask the model to respond with JSON and return it parsed.

    Raises:
        LLMUnavailableError: If Ollama is unreachable, the model isn't
            pulled yet, or the response isn't valid JSON.
    """
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            response = await client.post(
                "/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                },
            )
    except httpx.HTTPError as exc:
        raise LLMUnavailableError(
            f"Could not reach Ollama at {base_url}: {exc}"
        ) from exc

    if response.is_error:
        raise LLMUnavailableError(
            f"Ollama returned HTTP {response.status_code}: {response.text[:300]}"
        )

    try:
        body = response.json()
        return json.loads(body["response"])
    except (ValueError, KeyError, TypeError) as exc:
        raise LLMUnavailableError(
            f"Ollama returned an unparseable response: {exc}"
        ) from exc


async def is_model_present(model: str, *, base_url: str, timeout: float = 10.0) -> bool:
    """Whether `model` has already been pulled onto the Ollama server."""
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            response = await client.get("/api/tags")
    except httpx.HTTPError:
        return False
    if response.is_error:
        return False
    tags = response.json().get("models", [])
    return any(
        entry.get("name") == model or entry.get("model") == model for entry in tags
    )


async def pull_model(model: str, *, base_url: str, timeout: float = 1800.0) -> None:
    """Download `model` onto the Ollama server. Can take a long time for a
    large model — callers should run this as a background task rather
    than awaiting it inline in a request handler (see
    `app.features.settings.service.SettingsService.trigger_model_pull`).

    Raises:
        LLMUnavailableError: If the pull request itself fails. Ollama
            streams progress as newline-delimited JSON; this only checks
            the final line succeeded, it doesn't surface intermediate
            progress (the `/settings/llm/status` endpoint is polled for
            that instead).
        httpx.TimeoutException: if the pull is still going after `timeout`.
    """
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            async with client.stream(
                "POST", "/api/pull", json={"model": model, "stream": True}
            ) as response:
                if response.is_error:
                    body = await response.aread()
                    raise LLMUnavailableError(
                        f"Ollama pull failed with HTTP {response.status_code}: "
                        f"{body[:300]!r}"
                    )
                async for _ in response.aiter_lines():
                    pass  # draining the stream to let the pull run to completion
    except httpx.HTTPError as exc:
        raise LLMUnavailableError(
            f"Could not reach Ollama at {base_url}: {exc}"
        ) from exc
