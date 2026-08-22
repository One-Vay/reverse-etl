"""DataAgent: a goal-driven, LLM-assisted variant of a Sync.

Instead of transferring every row through a mapping on a fixed schedule,
a `DataAgent` analyzes newly-arrived rows against a user-described goal
and set of planned actions, and selects only the subset actually worth
loading — using the same local Ollama model already used for AI mapping
suggestions (see `app.core.llm`), not a separate ML stack. The selection
step itself lives in `app.features.agents.selector`; this module just
holds the persisted configuration and run history.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.features.destinations.models import Destination
    from app.features.mappings.models import Mapping


class AgentStatus(str, enum.Enum):
    """Lifecycle of an agent's configuration."""

    DRAFT = "draft"  # created, no plan generated yet — can't run
    READY = "ready"  # a plan exists, the agent can be run
    ARCHIVED = "archived"


class SelectionStrategy(str, enum.Enum):
    """How the agent frames its row-selection prompt to the LLM.

    This changes the *wording* of the prompt built in
    `app.features.agents.selector`, not the code path — every strategy
    ends up asking the model for the same {score, reason} JSON shape per
    row, just through a different lens (a purchase-probability estimate,
    a "does this belong to the matching cluster" judgment, or matching
    explicit criteria described in the goal/actions text).
    """

    SCORING = "scoring"
    CLUSTERING = "clustering"
    RULE_BASED = "rule_based"


class AgentRunStatus(str, enum.Enum):
    """Outcome of one execution of a `DataAgent`."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class DataAgent(Base, TimestampMixin):
    """A goal-driven data selection + sync configuration.

    Reuses an existing `Mapping` (source table, destination entity, field
    mappings) and `Destination` exactly like a `Sync` does — a `DataAgent`
    is a Sync with an LLM-driven filter in front of the write, triggered
    manually rather than on a schedule (the selection step is
    nondeterministic by nature, so an explicit "Run" keeps a human in the
    loop rather than auto-firing unreviewed writes).
    """

    __tablename__ = "data_agents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    destination_id: Mapped[int] = mapped_column(
        ForeignKey("destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mapping_id: Mapped[int] = mapped_column(
        ForeignKey("mappings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What the user is trying to accomplish (e.g. "increase conversion",
    # "move from B2C to B2B") and how they plan to act on the selected
    # rows (e.g. "direct calls", "email campaign") — both free text, fed
    # straight into the planning and selection prompts.
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    actions: Mapped[str] = mapped_column(Text, nullable=False)
    # User-supplied notes on specific columns worth the model's attention,
    # e.g. [{"column": "last_purchase_at", "description": "how recently
    # they bought — recency matters for conversion likelihood"}].
    feature_notes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    llm_model: Mapped[str] = mapped_column(String(255), nullable=False)
    selection_strategy: Mapped[SelectionStrategy] = mapped_column(
        String(20), nullable=False, default=SelectionStrategy.SCORING
    )
    selection_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.6
    )
    incremental_field: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[AgentStatus] = mapped_column(
        String(20), nullable=False, default=AgentStatus.DRAFT
    )

    # The LLM's plan: reasoning + a concrete selection rule description +
    # recommended next actions. See `app.features.agents.planner.AgentPlan`
    # for the exact shape. Stored as JSON rather than a dedicated table —
    # it's replaced wholesale on every "Generate plan", never queried by
    # field, just displayed.
    plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    plan_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    destination: Mapped["Destination"] = relationship(lazy="selectin")
    mapping: Mapped["Mapping"] = relationship(lazy="selectin")
    runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="AgentRun.started_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<DataAgent(id={self.id}, name='{self.name}', status='{self.status}')>"


class AgentRun(Base):
    """One execution of a `DataAgent`: how many rows it considered,
    selected via the LLM, and actually wrote to the destination."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    agent_id: Mapped[int] = mapped_column(
        ForeignKey("data_agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[AgentRunStatus] = mapped_column(String(20), nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    rows_considered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_selected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_written: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # The LLM's per-run explanation of what it selected and why — trimmed
    # to a reasonable size for display, not the full per-row reasoning.
    selection_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    agent: Mapped["DataAgent"] = relationship(back_populates="runs", lazy="selectin")

    @property
    def agent_name(self) -> str | None:
        """The owning agent's name, for display without a second lookup —
        exposed so `AgentRunRead.model_validate(run)` can pick it up
        directly via `from_attributes`."""
        return self.agent.name if self.agent is not None else None

    def __repr__(self) -> str:
        return (
            f"<AgentRun(id={self.id}, agent_id={self.agent_id}, "
            f"status='{self.status}')>"
        )
