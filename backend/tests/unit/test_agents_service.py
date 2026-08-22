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
    agent.annotation_field = overrides.get("annotation_field", None)
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

    message_repo = MagicMock()
    message_repo.get_by_agent = AsyncMock(return_value=[])

    _next_message_id = iter(range(1, 1000))

    async def _create_message(**kwargs):
        message = MagicMock()
        message.id = next(_next_message_id)
        message.agent_id = kwargs["agent_id"]
        message.role = kwargs["role"]
        message.content = kwargs["content"]
        message.created_at = kwargs["created_at"]
        return message

    message_repo.create = AsyncMock(side_effect=_create_message)

    return (
        agent_repo,
        destination_repo,
        mapping_repo,
        run_repo,
        settings_repo,
        message_repo,
    )


@pytest.fixture
def service(repos):
    (
        agent_repo,
        destination_repo,
        mapping_repo,
        run_repo,
        settings_repo,
        message_repo,
    ) = repos
    return AgentService(
        agent_repo,
        destination_repo,
        mapping_repo,
        run_repo,
        settings_repo,
        message_repo,
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
        _, _, _, _, settings_repo, _ = repos
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
        fake_run.row_details = []

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
        agent_repo, _, _, _, settings_repo, _ = repos
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
        fake_run.row_details = []

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


class TestPreview:
    @pytest.mark.asyncio
    async def test_raises_when_agent_has_no_plan_yet(self, service):
        with pytest.raises(ValidationError, match="Generate a plan"):
            await service.preview(1)

    @pytest.mark.asyncio
    async def test_returns_the_prepared_selection(self, service, repos):
        agent_repo, *_ = repos
        agent_repo.get_by_id = AsyncMock(
            return_value=make_agent(
                status=AgentStatus.READY, plan={"selection_rule": "x"}
            )
        )
        prepared = MagicMock()
        prepared.rows_considered = 5
        prepared.records_to_write = [{"EMAIL": "a@x.com"}]
        prepared.row_details = [
            {
                "index": 0,
                "score": 0.9,
                "reason": "hot",
                "selected": True,
                "record": {"EMAIL": "a@x.com"},
            }
        ]

        with patch(
            "app.features.agents.service.runner.preview",
            AsyncMock(return_value=prepared),
        ):
            result = await service.preview(1)

        assert result.rows_considered == 5
        assert result.rows_selected == 1
        assert result.row_details[0].score == 0.9

    @pytest.mark.asyncio
    async def test_raises_not_found_for_a_missing_agent(self, service, repos):
        agent_repo, *_ = repos
        agent_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.preview(999)


class TestChat:
    @pytest.mark.asyncio
    async def test_sends_a_message_and_persists_both_sides(self, service, repos):
        agent_repo, _, _, run_repo, _, message_repo = repos
        run_repo.get_by_agent = AsyncMock(return_value=[])

        with patch(
            "app.features.agents.service.agent_chat.reply",
            AsyncMock(return_value="Try mapping full_name to NAME as well."),
        ):
            result = await service.send_chat_message(1, "Why no name on the lead?")

        assert message_repo.create.await_count == 2
        assert result.user_message.content == "Why no name on the lead?"
        assert (
            result.assistant_message.content == "Try mapping full_name to NAME as well."
        )

    @pytest.mark.asyncio
    async def test_raises_when_llm_is_disabled(self, service, repos):
        _, _, _, _, settings_repo, _ = repos
        settings_repo.get = AsyncMock(return_value=MagicMock(llm_enabled=False))

        with pytest.raises(ValidationError):
            await service.send_chat_message(1, "hello")

    @pytest.mark.asyncio
    async def test_raises_not_found_for_a_missing_agent(self, service, repos):
        agent_repo, *_ = repos
        agent_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.send_chat_message(999, "hello")

    @pytest.mark.asyncio
    async def test_history_raises_not_found_for_a_missing_agent(self, service, repos):
        agent_repo, *_ = repos
        agent_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(NotFoundError):
            await service.get_chat_history(999)


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
