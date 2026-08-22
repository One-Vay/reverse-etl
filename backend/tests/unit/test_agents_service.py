"""Unit tests for AgentService, with repositories and the LLM mocked."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.features.agents.models import AgentRunStatus, AgentStatus, SelectionStrategy
from app.features.agents.schemas import AgentCreate, AgentPlan, AgentUpdate
from app.features.agents.service import AgentService


def make_agent(**overrides):
    agent = MagicMock()
    agent.id = overrides.get("id", 1)
    agent.name = overrides.get("name", "Conversion booster")
    agent.destination_id = overrides.get("destination_id", 1)
    agent.mapping_id = overrides.get("mapping_id", 1)
    agent.status = overrides.get("status", AgentStatus.DRAFT)
    agent.plan = overrides.get("plan", None)
    agent.plan_generated_at = overrides.get("plan_generated_at", None)
    agent.last_run_at = overrides.get("last_run_at", None)
    agent.goal = overrides.get("goal", "Increase conversion")
    agent.actions = overrides.get("actions", "Direct calls")
    agent.llm_model = overrides.get("llm_model", "qwen2.5:0.5b")
    agent.selection_strategy = overrides.get(
        "selection_strategy", SelectionStrategy.SCORING
    )
    agent.selection_threshold = overrides.get("selection_threshold", 0.6)
    agent.incremental_field = overrides.get("incremental_field", None)
    agent.feature_notes = overrides.get("feature_notes", [])
    agent.created_at = overrides.get("created_at", datetime.now(timezone.utc))
    agent.updated_at = overrides.get("updated_at", datetime.now(timezone.utc))

    mapping = MagicMock()
    mapping.source_id = overrides.get("source_id", 1)
    mapping.source_table = overrides.get("source_table", "customers")
    agent.mapping = mapping
    return agent


@pytest.fixture
def repos():
    agent_repo = MagicMock()
    agent_repo.session = MagicMock()
    agent_repo.get_by_id = AsyncMock(return_value=make_agent())
    agent_repo.get_all = AsyncMock(return_value=[])
    agent_repo.get_count = AsyncMock(return_value=0)
    agent_repo.create = AsyncMock(return_value=make_agent())
    agent_repo.update = AsyncMock(return_value=make_agent())
    agent_repo.update_plan = AsyncMock(
        return_value=make_agent(status=AgentStatus.READY)
    )
    agent_repo.delete = AsyncMock(return_value=True)

    destination_repo = MagicMock()
    destination_repo.get_by_id = AsyncMock(return_value=MagicMock(id=1))

    mapping_repo = MagicMock()
    mapping_repo.get_by_id = AsyncMock(return_value=MagicMock(id=1, source_id=1))

    run_repo = MagicMock()
    run_repo.count_by_agent = AsyncMock(return_value=0)
    run_repo.get_by_agent = AsyncMock(return_value=[])

    settings_repo = MagicMock()
    settings_repo.get = AsyncMock(
        return_value=MagicMock(
            llm_enabled=True,
            llm_base_url="http://ollama:11434",
            telegram_enabled=False,
            telegram_bot_token="",
            telegram_chat_id="",
        )
    )

    return agent_repo, destination_repo, mapping_repo, run_repo, settings_repo


@pytest.fixture
def service(repos):
    agent_repo, destination_repo, mapping_repo, run_repo, settings_repo = repos
    return AgentService(
        agent_repo, destination_repo, mapping_repo, run_repo, settings_repo
    )


class TestCreate:
    @pytest.mark.asyncio
    async def test_validates_destination_and_mapping_exist(self, service, repos):
        _, destination_repo, mapping_repo, *_ = repos
        destination_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.create(
                AgentCreate(
                    name="x",
                    destination_id=99,
                    mapping_id=1,
                    goal="g",
                    actions="a",
                    llm_model="m",
                )
            )

    @pytest.mark.asyncio
    async def test_creates_when_references_are_valid(self, service, repos):
        agent_repo, *_ = repos
        await service.create(
            AgentCreate(
                name="x",
                destination_id=1,
                mapping_id=1,
                goal="g",
                actions="a",
                llm_model="m",
            )
        )
        agent_repo.create.assert_awaited_once()


class TestGeneratePlan:
    @pytest.mark.asyncio
    async def test_raises_when_llm_is_disabled(self, service, repos):
        *_, settings_repo = repos
        settings_repo.get = AsyncMock(return_value=MagicMock(llm_enabled=False))

        with pytest.raises(ValidationError):
            await service.generate_plan(1)

    @pytest.mark.asyncio
    async def test_stores_the_generated_plan_and_marks_agent_ready(
        self, service, repos
    ):
        agent_repo, *_ = repos
        fake_plan = AgentPlan(
            strategy="scoring",
            reasoning="x",
            selection_rule="y",
            recommended_threshold=0.7,
            next_actions=[],
            model="qwen2.5:0.5b",
            generated_at=datetime.now(timezone.utc),
        )
        with (
            patch(
                "app.features.agents.service.SourceService"
            ) as mock_source_service_cls,
            patch(
                "app.features.agents.service._generate_plan",
                AsyncMock(return_value=fake_plan),
            ),
        ):
            mock_source_service_cls.return_value.get_table_schema = AsyncMock(
                return_value=[]
            )
            mock_source_service_cls.return_value.preview_table = AsyncMock(
                return_value=[]
            )
            await service.generate_plan(1)

        agent_repo.update_plan.assert_awaited_once()
        call_id, call_plan_dict, call_generated_at = (
            agent_repo.update_plan.call_args.args
        )
        assert call_id == 1
        assert call_plan_dict["strategy"] == "scoring"

    @pytest.mark.asyncio
    async def test_raises_not_found_for_a_missing_agent(self, service, repos):
        agent_repo, *_ = repos
        agent_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.generate_plan(999)


class TestRunNow:
    @pytest.mark.asyncio
    async def test_raises_when_agent_has_no_plan_yet(self, service):
        with pytest.raises(ValidationError, match="Generate a plan"):
            await service.run_now(1)

    @pytest.mark.asyncio
    async def test_runs_and_skips_telegram_when_disabled(self, service, repos):
        agent_repo, *_ = repos
        agent_repo.get_by_id = AsyncMock(
            return_value=make_agent(
                status=AgentStatus.READY, plan={"selection_rule": "x"}
            )
        )
        fake_run = MagicMock()
        fake_run.status = AgentRunStatus.SUCCESS
        fake_run.rows_considered = 10
        fake_run.rows_selected = 3
        fake_run.rows_written = 3
        fake_run.error_message = None
        fake_run.id = 1
        fake_run.agent_id = 1
        fake_run.agent_name = "Conversion booster"
        fake_run.started_at = datetime.now(timezone.utc)
        fake_run.finished_at = datetime.now(timezone.utc)
        fake_run.selection_summary = "Selected 3 of 10 rows."

        with (
            patch(
                "app.features.agents.service.runner.execute",
                AsyncMock(return_value=fake_run),
            ),
            patch(
                "app.features.agents.service.telegram.send_message", AsyncMock()
            ) as mock_send,
        ):
            result = await service.run_now(1)

        mock_send.assert_not_awaited()
        assert result.rows_written == 3

    @pytest.mark.asyncio
    async def test_sends_a_telegram_report_when_enabled(self, service, repos):
        agent_repo, _, _, _, settings_repo = repos
        agent_repo.get_by_id = AsyncMock(
            return_value=make_agent(
                status=AgentStatus.READY, plan={"selection_rule": "x"}
            )
        )
        settings_repo.get = AsyncMock(
            return_value=MagicMock(
                llm_enabled=True,
                llm_base_url="http://ollama:11434",
                telegram_enabled=True,
                telegram_bot_token="token",
                telegram_chat_id="chat",
            )
        )
        fake_run = MagicMock()
        fake_run.status = AgentRunStatus.SUCCESS
        fake_run.rows_considered = 10
        fake_run.rows_selected = 3
        fake_run.rows_written = 3
        fake_run.error_message = None
        fake_run.id = 1
        fake_run.agent_id = 1
        fake_run.agent_name = "Conversion booster"
        fake_run.started_at = datetime.now(timezone.utc)
        fake_run.finished_at = datetime.now(timezone.utc)
        fake_run.selection_summary = "Selected 3 of 10 rows."

        with (
            patch(
                "app.features.agents.service.runner.execute",
                AsyncMock(return_value=fake_run),
            ),
            patch(
                "app.features.agents.service.telegram.send_message", AsyncMock()
            ) as mock_send,
        ):
            await service.run_now(1)

        mock_send.assert_awaited_once()
        args = mock_send.call_args.args
        assert args[0] == "token"
        assert args[1] == "chat"

    @pytest.mark.asyncio
    async def test_raises_not_found_for_a_missing_agent(self, service, repos):
        agent_repo, *_ = repos
        agent_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.run_now(999)


class TestUpdate:
    @pytest.mark.asyncio
    async def test_raises_not_found_when_destination_is_invalid(self, service, repos):
        _, destination_repo, *_ = repos
        destination_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.update(1, AgentUpdate(destination_id=999))


class TestDelete:
    @pytest.mark.asyncio
    async def test_raises_not_found_for_a_missing_agent(self, service, repos):
        agent_repo, *_ = repos
        agent_repo.delete = AsyncMock(return_value=False)

        with pytest.raises(NotFoundError):
            await service.delete(999)
