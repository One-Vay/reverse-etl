"""Pydantic schemas for Mapping entity."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MappingBase(BaseModel):
    """Base schema with common mapping fields."""

    name: str = Field(..., min_length=1, max_length=255)
    source_id: int
    source_table: str = Field(..., min_length=1)
    destination_entity: str = Field(..., min_length=1)
    field_mappings: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("field_mappings")
    @classmethod
    def validate_field_mappings(cls, v: list) -> list:
        if not v:
            return v
        for item in v:
            if not isinstance(item, dict):
                raise TypeError("Each field mapping must be a dictionary")
            if "source_field" not in item or "destination_field" not in item:
                raise ValueError(
                    "Each field mapping must contain 'source_field' and 'destination_field'"
                )
        return v


class MappingCreate(MappingBase):
    """Schema for creating a new mapping."""


class MappingUpdate(BaseModel):
    """Schema for updating an existing mapping (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    source_id: int | None = None
    source_table: str | None = Field(None, min_length=1)
    destination_entity: str | None = Field(None, min_length=1)
    field_mappings: list[dict[str, Any]] | None = None


class MappingRead(BaseModel):
    """Schema for reading mapping data."""

    id: int
    name: str
    source_id: int
    source_table: str
    destination_entity: str
    field_mappings: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MappingListResponse(BaseModel):
    """Schema for paginated list of mappings."""

    items: list[MappingRead]
    total: int
    skip: int
    limit: int


class SuggestFieldInfo(BaseModel):
    """One field offered to the AI mapping suggester — just enough to
    reason about a match (name + type), not a full `ColumnSchema`."""

    name: str
    data_type: str = ""


class SuggestMappingsRequest(BaseModel):
    """Fields already fetched by the frontend's SourceColumnPicker /
    destination-fields query — the suggester never fetches these itself,
    it only reasons about the two lists it's given."""

    source_columns: list[SuggestFieldInfo] = Field(..., min_length=1)
    destination_fields: list[SuggestFieldInfo] = Field(..., min_length=1)


class SuggestedFieldPair(BaseModel):
    source_field: str
    destination_field: str
    confidence: float = Field(ge=0, le=1)


class SuggestMappingsResponse(BaseModel):
    """`pairs` is empty (with `message` explaining why) whenever AI
    suggestions aren't usable — disabled, unreachable, or the model
    returned nothing sane — never an HTTP error, so a missing/misbehaving
    LLM never blocks the manual mapping flow."""

    pairs: list[SuggestedFieldPair]
    message: str | None = None
