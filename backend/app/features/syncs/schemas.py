"""Pydantic schemas for Sync entity."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.features.destinations.schemas import DestinationRead
from app.features.mappings.schemas import MappingRead
from app.features.sources.schemas import SourceRead
from app.features.syncs.models import SyncStatus


class SyncBase(BaseModel):
    """Base schema with common sync fields."""

    name: str = Field(..., min_length=1, max_length=255)
    source_id: int
    destination_id: int
    mapping_id: int
    schedule: str = Field(..., min_length=1)
    incremental_field: str | None = Field(None, max_length=255)
    status: SyncStatus = SyncStatus.ACTIVE


class SyncCreate(SyncBase):
    """Schema for creating a new sync."""


class SyncUpdate(BaseModel):
    """Schema for updating an existing sync (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    source_id: int | None = None
    destination_id: int | None = None
    mapping_id: int | None = None
    schedule: str | None = Field(None, min_length=1)
    incremental_field: str | None = Field(None, max_length=255)
    status: SyncStatus | None = None


class SyncRead(BaseModel):
    """Schema for reading sync data with nested relations."""

    id: int
    name: str
    source_id: int
    destination_id: int
    mapping_id: int
    schedule: str
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
