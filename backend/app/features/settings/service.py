"""Service layer for AppSettings, plus the local-LLM pull/status glue."""

from __future__ import annotations

import asyncio
import logging

from app.core import llm
from app.features.settings.repository import SettingsRepository
from app.features.settings.schemas import AppSettingsRead, AppSettingsUpdate, LLMStatus

logger = logging.getLogger(__name__)

# Whether a model pull is currently in flight, keyed by (base_url, model).
# Process-local, in-memory — deliberately not persisted: this app runs as
# a single process (see backend/Dockerfile/entrypoint.sh), so there's
# nothing to coordinate across workers, and a pull that was "in progress"
# when the process restarted should just be re-triggerable, not resumed.
_pulling: set[tuple[str, str]] = set()


class SettingsService:
    """Business logic for the singleton app settings row."""

    def __init__(self, repository: SettingsRepository):
        self.repository = repository

    async def get(self) -> AppSettingsRead:
        settings = await self.repository.get()
        return AppSettingsRead.model_validate(settings)

    async def update(self, data: AppSettingsUpdate) -> AppSettingsRead:
        settings = await self.repository.update(data)
        if data.llm_enabled:
            self.trigger_model_pull(settings.llm_base_url, settings.llm_model)
        return AppSettingsRead.model_validate(settings)

    async def get_llm_status(self) -> LLMStatus:
        settings = await self.repository.get()
        key = (settings.llm_base_url, settings.llm_model)
        if key in _pulling:
            return LLMStatus(
                model_present=False,
                pulling=True,
                detail=f"Pulling {settings.llm_model}…",
            )

        present = await llm.is_model_present(
            settings.llm_model, base_url=settings.llm_base_url
        )
        return LLMStatus(model_present=present, pulling=False)

    def trigger_model_pull(self, base_url: str, model: str) -> None:
        """Kick off a model pull in the background — never awaited by the
        request that calls this, since a pull can take minutes. Progress
        is observed via `get_llm_status`, not this call's return value."""
        key = (base_url, model)
        if key in _pulling:
            return
        _pulling.add(key)

        async def _run() -> None:
            try:
                if not await llm.is_model_present(model, base_url=base_url):
                    await llm.pull_model(model, base_url=base_url)
            except Exception:
                logger.exception("Background pull of Ollama model %r failed", model)
            finally:
                _pulling.discard(key)

        asyncio.create_task(_run())  # noqa: RUF006 - intentionally fire-and-forget
