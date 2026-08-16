"""Pydantic schemas for Destination entity."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, SecretStr, field_validator

from app.features.destinations.models import DestinationType


class DestinationBase(BaseModel):
    """Base schema with common destination fields."""

    name: str = Field(..., min_length=1, max_length=255)
    type: DestinationType
    api_url: str = Field(..., min_length=1)
    auth_token: SecretStr

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v: str) -> DestinationType:
        if isinstance(v, DestinationType):
            return v
        try:
            return DestinationType(v.lower())
        except ValueError:
            raise ValueError(f"Invalid destination type: {v}")


class DestinationCreate(DestinationBase):
    """Schema for creating a new destination."""
    pass


class DestinationUpdate(BaseModel):
    """Schema for updating an existing destination (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[DestinationType] = None
    api_url: Optional[str] = Field(None, min_length=1)
    auth_token: Optional[SecretStr] = None


class DestinationRead(BaseModel):
    """Schema for reading destination data (auth_token excluded)."""

    id: int
    name: str
    type: DestinationType
    api_url: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DestinationListResponse(BaseModel):
    """Schema for paginated list of destinations."""

    items: list[DestinationRead]
    total: int
    skip: int
    limit: int