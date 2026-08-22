"""Pydantic schemas for Sync entity."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.features.destinations.schemas import DestinationRead
from app.features.mappings.schemas import MappingRead
from app.features.sources.schemas import SourceRead
from app.features.syncs.models import (
    IntervalUnit,
    SyncRunStatus,
    SyncRunTrigger,
    SyncStatus,
)

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _validate_run_at_time(value: str | None) -> str | None:
    if value is not None and not _TIME_RE.match(value):
        raise ValueError("run_at_time must be in HH:MM (24h) format")
    return value


class SyncBase(BaseModel):
    """Base schema with common sync fields."""

    name: str = Field(..., min_length=1, max_length=255)
    source_id: int
    destination_id: int
    mapping_id: int
    interval_value: int = Field(..., ge=1, le=168)
    interval_unit: IntervalUnit = IntervalUnit.HOURS
    run_at_time: str | None = Field(
        None, description="HH:MM, only used when interval_unit is 'days'"
    )
    incremental_field: str | None = Field(None, max_length=255)
    status: SyncStatus = SyncStatus.ACTIVE

    _validate_time = field_validator("run_at_time")(_validate_run_at_time)

    @model_validator(mode="after")
    def _check_interval_bounds(self) -> "SyncBase":
        max_value = 168 if self.interval_unit == IntervalUnit.HOURS else 90
        if self.interval_value > max_value:
            raise ValueError(
                f"interval_value must be at most {max_value} for '{self.interval_unit.value}'"
            )
        return self


class SyncCreate(SyncBase):
    """Schema for creating a new sync."""


class SyncUpdate(BaseModel):
    """Schema for updating an existing sync (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    source_id: int | None = None
    destination_id: int | None = None
    mapping_id: int | None = None
    interval_value: int | None = Field(None, ge=1, le=168)
    interval_unit: IntervalUnit | None = None
    run_at_time: str | None = Field(
        None, description="HH:MM, only used when interval_unit is 'days'"
    )
    incremental_field: str | None = Field(None, max_length=255)
    status: SyncStatus | None = None

    _validate_time = field_validator("run_at_time")(_validate_run_at_time)


class SyncRead(BaseModel):
    """Schema for reading sync data with nested relations."""

    id: int
    name: str
    source_id: int
    destination_id: int
    mapping_id: int
    interval_value: int
    interval_unit: IntervalUnit
    run_at_time: str | None
    incremental_field: str | None
    last_run: datetime | None
    next_run: datetime | None
    status: SyncStatus
    created_at: datetime
    updated_at: datetime

    # Optional nested relations (for detail endpoints)
    source: SourceRead | None = None
    destination: DestinationRead | None = None
    mapping: MappingRead | None = None

    model_config = {"from_attributes": True}


class SyncListResponse(BaseModel):
    """Schema for paginated list of syncs."""

    items: list[SyncRead]
    total: int
    skip: int
    limit: int


class SyncRunRead(BaseModel):
    """Schema for reading one sync run's result."""

    id: int
    sync_id: int
    status: SyncRunStatus
    trigger: SyncRunTrigger
    started_at: datetime
    finished_at: datetime | None
    records_read: int
    records_written: int
    error_message: str | None
    sync_name: str | None = None

    model_config = {"from_attributes": True}


class SyncRunListResponse(BaseModel):
    """Schema for paginated list of sync runs."""

    items: list[SyncRunRead]
    total: int
    skip: int
    limit: int


class UpcomingSyncRuns(BaseModel):
    """Projected future fire times for one active sync, for the dashboard's
    upcoming-runs calendar."""

    sync_id: int
    sync_name: str
    occurrences: list[datetime]
