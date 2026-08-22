"""Pydantic schemas for DataAgent and AgentRun."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.features.agents.models import (
    AgentRunStatus,
    AgentStatus,
    ChatRole,
    SelectionStrategy,
)


class FeatureNote(BaseModel):
    """A user-supplied hint about one column, fed into the planning and
    selection prompts so the LLM knows why a column matters instead of
    just its name and type."""

    column: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=1000)


class AgentBase(BaseModel):
    """Base schema with fields common to create/read."""

    name: str = Field(..., min_length=1, max_length=255)
    destination_id: int
    mapping_id: int
    goal: str = Field(..., min_length=1, max_length=4000)
    actions: str = Field(..., min_length=1, max_length=4000)
    feature_notes: list[FeatureNote] = Field(default_factory=list)
    llm_model: str = Field(..., min_length=1, max_length=255)
    selection_strategy: SelectionStrategy = SelectionStrategy.SCORING
    selection_threshold: float = Field(0.6, ge=0.0, le=1.0)
    incremental_field: str | None = Field(None, max_length=255)
    annotation_field: str | None = Field(
        None,
        max_length=255,
        description=(
            "Destination field to receive a human-readable note (the "
            "selection score and the model's reason) on every record this "
            "agent writes, e.g. 'COMMENTS' — without it, nothing on the "
            "written record explains why it was loaded."
        ),
    )


class AgentCreate(AgentBase):
    """Schema for creating a new agent — always starts as DRAFT until a
    plan is generated (see `POST /agents/{id}/plan`), so `status` isn't
    accepted here."""


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    destination_id: int | None = None
    mapping_id: int | None = None
    goal: str | None = Field(None, min_length=1, max_length=4000)
    actions: str | None = Field(None, min_length=1, max_length=4000)
    feature_notes: list[FeatureNote] | None = None
    llm_model: str | None = Field(None, min_length=1, max_length=255)
    selection_strategy: SelectionStrategy | None = None
    selection_threshold: float | None = Field(None, ge=0.0, le=1.0)
    incremental_field: str | None = Field(None, max_length=255)
    annotation_field: str | None = Field(None, max_length=255)
    status: AgentStatus | None = None


class AgentPlan(BaseModel):
    """The LLM's plan for one agent — generated fresh on every
    `POST /agents/{id}/plan` call and stored wholesale on the agent.

    `reasoning` is deliberately unbounded free text: since the model runs
    entirely locally, there's no reason to truncate or sanitize its
    analysis before showing it to the user.
    """

    strategy: SelectionStrategy
    reasoning: str
    selection_rule: str
    recommended_threshold: float | None = Field(None, ge=0.0, le=1.0)
    next_actions: list[str] = Field(default_factory=list)
    model: str
    generated_at: datetime


class AgentRead(BaseModel):
    """Schema for reading agent data."""

    id: int
    name: str
    destination_id: int
    mapping_id: int
    goal: str
    actions: str
    feature_notes: list[dict[str, Any]]
    llm_model: str
    selection_strategy: SelectionStrategy
    selection_threshold: float
    incremental_field: str | None
    annotation_field: str | None
    status: AgentStatus
    plan: dict[str, Any] | None
    plan_generated_at: datetime | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    items: list[AgentRead]
    total: int
    skip: int
    limit: int


class RowDetail(BaseModel):
    """One considered row's outcome — the full breakdown behind
    `selection_summary`, rendered as a table in the console so a person
    can see exactly what was sent to the destination and why, without
    cross-referencing the destination system itself."""

    index: int
    score: float
    reason: str
    selected: bool
    record: dict[str, Any] | None = None


class AgentRunRead(BaseModel):
    """Schema for reading one agent run's result."""

    id: int
    agent_id: int
    agent_name: str | None = None
    status: AgentRunStatus
    started_at: datetime
    finished_at: datetime | None
    rows_considered: int
    rows_selected: int
    rows_written: int
    selection_summary: str | None
    row_details: list[RowDetail]
    error_message: str | None

    model_config = {"from_attributes": True}


class AgentRunListResponse(BaseModel):
    items: list[AgentRunRead]
    total: int
    skip: int
    limit: int


class AgentPreview(BaseModel):
    """Result of a dry run: scores every currently-due row against the
    agent's plan exactly like a real run would, but never writes anything
    — the step between "Generate plan" and "Run now" that lets a user see
    precisely what would happen before committing to it."""

    rows_considered: int
    rows_selected: int
    row_details: list[RowDetail]


class ChatMessageRead(BaseModel):
    id: int
    agent_id: int
    role: ChatRole
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    """The new exchange from one chat turn — the user's message (as
    stored) and the assistant's reply, so the frontend can append both
    without re-fetching the whole thread."""

    user_message: ChatMessageRead
    assistant_message: ChatMessageRead


class LLMModelPullRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=255)


class LLMModelStatus(BaseModel):
    """Whether a specific named model is ready to use — same shape as
    Settings' `LLMStatus` but for an arbitrary model name rather than the
    one globally-configured one, since each agent can pick its own."""

    model: str
    present: bool
    pulling: bool
