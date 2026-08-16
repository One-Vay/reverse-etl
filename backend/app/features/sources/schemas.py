"""Pydantic schemas for Source entity."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, SecretStr, field_validator

from app.features.sources.models import SourceType


class SourceBase(BaseModel):
    """Base schema with common source fields."""

    name: str = Field(..., min_length=1, max_length=255)
    type: SourceType
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: SecretStr

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: str) -> SourceType:
        if isinstance(v, SourceType):
            return v
        try:
            return SourceType(v.lower())
        except ValueError:
            raise ValueError(f"Invalid source type: {v}")


class SourceCreate(SourceBase):
    """Schema for creating a new source."""
    pass


class SourceUpdate(BaseModel):
    """Schema for updating an existing source (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[SourceType] = None
    host: Optional[str] = Field(None, min_length=1)
    port: Optional[int] = Field(None, ge=1, le=65535)
    database: Optional[str] = Field(None, min_length=1)
    username: Optional[str] = Field(None, min_length=1)
    password: Optional[SecretStr] = None


class SourceRead(BaseModel):
    """Schema for reading source data (password excluded)."""

    id: int
    name: str
    type: SourceType
    host: str
    port: int
    database: str
    username: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceListResponse(BaseModel):
    """Schema for paginated list of sources."""

    items: list[SourceRead]
    total: int
    skip: int
    limit: int