"""Unit tests for the agent execution engine, with connectors, the LLM
selector, and repositories mocked — no real DB or network access."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connectors.base import ConnectionFailedError
from app.features.agents import runner
from app.features.agents.models import AgentRunStatus, SelectionStrategy
from app.features.agents.selector import RowScore


def make_agent(**overrides):
    agent = MagicMock()
    agent.id = overrides.get("id", 1)
    agent.destination_id = overrides.get("destination_id", 20)
    agent.goal = overrides.get("goal", "Increase conversion")
    agent.actions = overrides.get("actions", "Direct calls")
    agent.llm_model = overrides.get("llm_model", "qwen2.5:0.5b")
    agent.selection_strategy = overrides.get(
        "selection_strategy", SelectionStrategy.SCORING
    )
    agent.selection_threshold = overrides.get("selection_threshold", 0.5)
    agent.incremental_field = overrides.get("incremental_field", None)
    agent.last_run_at = overrides.get("last_run_at", None)
    agent.feature_notes = overrides.get("feature_notes", [])
    agent.plan = overrides.get("plan", {"selection_rule": "score by recency"})

    mapping = MagicMock()
    mapping.source_id = overrides.get("source_id", 10)
    mapping.source_table = overrides.get("source_table", "customers")
    mapping.destination_entity = overrides.get("destination_entity", "lead")
    mapping.field_mappings = overrides.get(
        "field_mappings",
        [{"source_field": "email", "destination_field": "EMAIL", "transformation": ""}],
    )
    agent.mapping = mapping
    return agent


def make_source_connector(rows):
    connector = AsyncMock()
    connector.fetch_data = AsyncMock(return_value=rows)
    connector.__aenter__ = AsyncMock(return_value=connector)
    connector.__aexit__ = AsyncMock(return_value=None)
    return connector


def make_destination_connector(written=1):
    connector = AsyncMock()
    connector.upsert_data = AsyncMock(return_value=written)
    connector.__aenter__ = AsyncMock(return_value=connector)
    connector.__aexit__ = AsyncMock(return_value=None)
    return connector


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def mock_run_repo():
    repo = MagicMock()

    async def _create(**kwargs):
        run = MagicMock()
        for key, value in kwargs.items():
            setattr(run, key, value)
        return run

    repo.create = AsyncMock(side_effect=_create)
    return repo


@pytest.fixture
def mock_agent_repo():
    repo = MagicMock()
    repo.update_last_run = AsyncMock()
    return repo


@pytest.fixture
def mock_app_settings():
    settings = MagicMock()
    settings.llm_enabled = True
    settings.llm_base_url = "http://ollama:11434"
    return settings


class TestExecute:
    @pytest.mark.asyncio
    async def test_writes_only_rows_above_the_threshold(
        self, mock_session, mock_run_repo, mock_agent_repo, mock_app_settings
    ):
        agent = make_agent(selection_threshold=0.5)
        rows = [{"email": "a@x.com"}, {"email": "b@x.com"}, {"email": "c@x.com"}]
        scores = [
            RowScore(index=0, score=0.9, reason="hot lead"),
            RowScore(index=1, score=0.2, reason="cold"),
            RowScore(index=2, score=0.6, reason="warm"),
        ]

        with (
            patch(
                "app.features.agents.runner.SettingsRepository",
                return_value=MagicMock(get=AsyncMock(return_value=mock_app_settings)),
            ),
            patch(
                "app.features.agents.runner.SourceService"
            ) as mock_source_service_cls,
            patch(
                "app.features.agents.runner.DestinationService"
            ) as mock_dest_service_cls,
            patch(
                "app.features.agents.runner.score_rows", AsyncMock(return_value=scores)
            ),
            patch(
                "app.features.agents.runner.AgentRunRepository",
                return_value=mock_run_repo,
            ),
            patch(
                "app.features.agents.runner.AgentRepository",
                return_value=mock_agent_repo,
            ),
        ):
            source_connector = make_source_connector(rows)
            mock_source_service_cls.return_value.build_connector = AsyncMock(
                return_value=source_connector
            )
            dest_connector = make_destination_connector(written=2)
            mock_dest_service_cls.return_value.build_connector = AsyncMock(
                return_value=dest_connector
            )

            run = await runner.execute(agent, session=mock_session)

        dest_connector.upsert_data.assert_awaited_once()
        entity, records = dest_connector.upsert_data.call_args.args
        assert entity == "lead"
        assert records == [{"EMAIL": "a@x.com"}, {"EMAIL": "c@x.com"}]
        assert run.status == AgentRunStatus.SUCCESS
        assert run.rows_considered == 3
        assert run.rows_selected == 2
        assert run.rows_written == 2
        mock_agent_repo.update_last_run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_rows_above_threshold_skips_the_destination_write(
        self, mock_session, mock_run_repo, mock_agent_repo, mock_app_settings
    ):
        agent = make_agent(selection_threshold=0.9)
        rows = [{"email": "a@x.com"}]
        scores = [RowScore(index=0, score=0.1, reason="cold")]

        with (
            patch(
                "app.features.agents.runner.SettingsRepository",
                return_value=MagicMock(get=AsyncMock(return_value=mock_app_settings)),
            ),
            patch(
                "app.features.agents.runner.SourceService"
            ) as mock_source_service_cls,
            patch(
                "app.features.agents.runner.DestinationService"
            ) as mock_dest_service_cls,
            patch(
                "app.features.agents.runner.score_rows", AsyncMock(return_value=scores)
            ),
            patch(
                "app.features.agents.runner.AgentRunRepository",
                return_value=mock_run_repo,
            ),
            patch(
                "app.features.agents.runner.AgentRepository",
                return_value=mock_agent_repo,
            ),
        ):
            source_connector = make_source_connector(rows)
            mock_source_service_cls.return_value.build_connector = AsyncMock(
                return_value=source_connector
            )
            dest_connector = make_destination_connector()
            mock_dest_service_cls.return_value.build_connector = AsyncMock(
                return_value=dest_connector
            )

            run = await runner.execute(agent, session=mock_session)

        dest_connector.upsert_data.assert_not_awaited()
        assert run.rows_selected == 0
        assert run.rows_written == 0
        assert run.status == AgentRunStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_fails_gracefully_when_llm_is_disabled(
        self, mock_session, mock_run_repo, mock_agent_repo
    ):
        agent = make_agent()
        disabled_settings = MagicMock(llm_enabled=False)

        with (
            patch(
                "app.features.agents.runner.SettingsRepository",
                return_value=MagicMock(get=AsyncMock(return_value=disabled_settings)),
            ),
            patch(
                "app.features.agents.runner.AgentRunRepository",
                return_value=mock_run_repo,
            ),
            patch(
                "app.features.agents.runner.AgentRepository",
                return_value=mock_agent_repo,
            ),
        ):
            run = await runner.execute(agent, session=mock_session)

        assert run.status == AgentRunStatus.FAILED
        assert "enabled in Settings" in run.error_message

    @pytest.mark.asyncio
    async def test_connector_failure_is_recorded_not_raised(
        self, mock_session, mock_run_repo, mock_agent_repo, mock_app_settings
    ):
        agent = make_agent()

        with (
            patch(
                "app.features.agents.runner.SettingsRepository",
                return_value=MagicMock(get=AsyncMock(return_value=mock_app_settings)),
            ),
            patch(
                "app.features.agents.runner.SourceService"
            ) as mock_source_service_cls,
            patch(
                "app.features.agents.runner.AgentRunRepository",
                return_value=mock_run_repo,
            ),
            patch(
                "app.features.agents.runner.AgentRepository",
                return_value=mock_agent_repo,
            ),
        ):
            mock_source_service_cls.return_value.build_connector = AsyncMock(
                side_effect=ConnectionFailedError("bad credentials")
            )
            run = await runner.execute(agent, session=mock_session)

        assert run.status == AgentRunStatus.FAILED
        assert run.error_message == "bad credentials"

    def test_incremental_where_uses_last_run_at(self):
        agent = make_agent(
            incremental_field="updated_at",
            last_run_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        where = runner._incremental_where(agent)
        assert where == "updated_at > '2026-01-01T00:00:00+00:00'"

    def test_incremental_where_is_none_on_first_run(self):
        agent = make_agent(incremental_field="updated_at", last_run_at=None)
        assert runner._incremental_where(agent) is None
