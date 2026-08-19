"""Pydantic schemas for Destination entity."""

from datetime import datetime

from pydantic import BaseModel, Field, SecretStr, field_validator

from app.features.destinations.models import DestinationType


class DestinationBase(BaseModel):
    """Base schema with common destination fields."""

    name: str = Field(..., min_length=1, max_length=255)
    type: DestinationType
    api_url: str = Field(..., min_length=1)
    auth_token: SecretStr
    request_timeout: float | None = Field(None, gt=0, le=300)

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


class DestinationUpdate(BaseModel):
    """Schema for updating an existing destination (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    type: DestinationType | None = None
    api_url: str | None = Field(None, min_length=1)
    auth_token: SecretStr | None = None
    request_timeout: float | None = Field(None, gt=0, le=300)


class DestinationRead(BaseModel):
    """Schema for reading destination data (auth_token excluded)."""

    id: int
    name: str
    type: DestinationType
    api_url: str
    request_timeout: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DestinationListResponse(BaseModel):
    """Schema for paginated list of destinations."""

    items: list[DestinationRead]
    total: int
    skip: int
    limit: int


class ConnectionTestResult(BaseModel):
    """Result of a `test_connection()` call against a destination's connector."""

    success: bool
    message: str


class EntityFieldRead(BaseModel):
    """One field of a destination entity, for interactive field-mapping."""

    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool

    model_config = {"from_attributes": True}
