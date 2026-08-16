"""Pydantic schemas for Mapping entity."""

from datetime import datetime
from typing import Optional, Any
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
                raise ValueError("Each field mapping must be a dictionary")
            if "source_field" not in item or "destination_field" not in item:
                raise ValueError(
                    "Each field mapping must contain 'source_field' and 'destination_field'"
                )
        return v


class MappingCreate(MappingBase):
    """Schema for creating a new mapping."""
    pass


class MappingUpdate(BaseModel):
    """Schema for updating an existing mapping (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    source_id: Optional[int] = None
    source_table: Optional[str] = Field(None, min_length=1)
    destination_entity: Optional[str] = Field(None, min_length=1)
    field_mappings: Optional[list[dict[str, Any]]] = None


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