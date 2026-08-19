"""Pydantic schemas for Source entity."""

from datetime import datetime
from typing import Any, Literal

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

    # Advanced, optional — null/omitted means "use the connector's own
    # default". Not every field applies to every source type (e.g.
    # ClickHouse ignores command_timeout/pool sizes); unused ones are
    # simply not sent to that type's connector.
    connect_timeout: float | None = Field(None, gt=0, le=300)
    command_timeout: float | None = Field(None, gt=0, le=300)
    min_pool_size: int | None = Field(None, ge=1, le=100)
    max_pool_size: int | None = Field(None, ge=1, le=100)

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


class SourceUpdate(BaseModel):
    """Schema for updating an existing source (all fields optional)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    type: SourceType | None = None
    host: str | None = Field(None, min_length=1)
    port: int | None = Field(None, ge=1, le=65535)
    database: str | None = Field(None, min_length=1)
    username: str | None = Field(None, min_length=1)
    password: SecretStr | None = None
    connect_timeout: float | None = Field(None, gt=0, le=300)
    command_timeout: float | None = Field(None, gt=0, le=300)
    min_pool_size: int | None = Field(None, ge=1, le=100)
    max_pool_size: int | None = Field(None, ge=1, le=100)


class SourceRead(BaseModel):
    """Schema for reading source data (password excluded)."""

    id: int
    name: str
    type: SourceType
    host: str
    port: int
    database: str
    username: str
    connect_timeout: float | None = None
    command_timeout: float | None = None
    min_pool_size: int | None = None
    max_pool_size: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceListResponse(BaseModel):
    """Schema for paginated list of sources."""

    items: list[SourceRead]
    total: int
    skip: int
    limit: int


class ConnectionTestResult(BaseModel):
    """Result of a `test_connection()` call against a source's connector."""

    success: bool
    message: str


class TableInfoRead(BaseModel):
    """One table or view discovered on a source, for schema browsing."""

    name: str
    # Named schema_name (not schema) to avoid shadowing BaseModel.schema();
    # the alias keeps the wire format ({"schema": "..."}) unaffected and
    # still matches TableInfo.schema for from_attributes validation.
    schema_name: str = Field(alias="schema")
    kind: Literal["table", "view"]

    model_config = {"from_attributes": True, "populate_by_name": True}


class ColumnInfoRead(BaseModel):
    """One column of a table/view, for interactive field-mapping."""

    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool

    model_config = {"from_attributes": True}


class TablePreviewResponse(BaseModel):
    """A small sample of rows read from a source table, for the mapping UI."""

    columns: list[str]
    rows: list[dict[str, Any]]
