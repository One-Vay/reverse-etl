"""Pydantic schemas for Sync entity."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.features.syncs.models import SyncStatus
from app.features.sources.schemas import SourceRead
from app.features.destinations.schemas import DestinationRead
from app.features.mappings.schemas import MappingRead


class SyncBase(BaseModel):
    """Base schema with common sync fields."""

    name: str = Field(..., min_length=1, max_length=255)
    source_id: int
    destination_id: int
    mapping_id: int
    schedule: str = Field(..., min_length=1)
    incremental_field: Optional[str] = Field(None, max_length=255)
    status: SyncStatus = SyncStatus.ACTIVE


class SyncCreate(SyncBase):
    """Schema for creating a new sync."""
    pass


class SyncUpdate(BaseModel):
    """Schema for updating an existing sync (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    source_id: Optional[int] = None
    destination_id: Optional[int] = None
    mapping_id: Optional[int] = None
    schedule: Optional[str] = Field(None, min_length=1)
    incremental_field: Optional[str] = Field(None, max_length=255)
    status: Optional[SyncStatus] = None


class SyncRead(BaseModel):
    """Schema for reading sync data with nested relations."""

    id: int
    name: str
    source_id: int
    destination_id: int
    mapping_id: int
    schedule: str
    incremental_field: Optional[str]
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    status: SyncStatus
    created_at: datetime
    updated_at: datetime

    # Optional nested relations (for detail endpoints)
    source: Optional[SourceRead] = None
    destination: Optional[DestinationRead] = None
    mapping: Optional[MappingRead] = None

    model_config = {"from_attributes": True}


class SyncListResponse(BaseModel):
    """Schema for paginated list of syncs."""

    items: list[SyncRead]
    total: int
    skip: int
    limit: int