"""Service layer for Source entity."""

from typing import Any

from app.connectors.base import ColumnSchema, SourceConnector, TableInfo
from app.connectors.factory import ConnectorFactory
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import decrypt_password, encrypt_password
from app.features.sources.repository import SourceRepository
from app.features.sources.models import SourceType
from app.features.sources.schemas import (
    SourceCreate,
    SourceListResponse,
    SourceRead,
    SourceUpdate,
)

# Which of a source's "advanced" columns each connector type actually
# accepts — passing an unsupported one would raise a TypeError from the
# connector's own __init__, so each type only forwards what it understands.
# (e.g. ClickHouseConnector has no connection pool, only a request timeout.)
_ADVANCED_FIELDS_BY_TYPE: dict[SourceType, tuple[str, ...]] = {
    SourceType.POSTGRES: (
        "connect_timeout",
        "command_timeout",
        "min_pool_size",
        "max_pool_size",
    ),
    SourceType.CLICKHOUSE: ("connect_timeout",),
}


class SourceService:
    """Business logic for sources."""

    def __init__(self, repository: SourceRepository):
        self.repository = repository

    async def build_connector(self, id: int) -> SourceConnector:
        """Look up a source and build a connector for it, with its
        password decrypted. Raises NotFoundError if the source doesn't
        exist; propagates UnknownConnectorTypeError from the factory if
        the source's type has no connector registered."""
        source = await self.repository.get_by_id(id)
        if not source:
            raise NotFoundError(f"Source with id {id} not found")

        password = decrypt_password(source.password)
        advanced: dict[str, Any] = {
            field: getattr(source, field)
            for field in _ADVANCED_FIELDS_BY_TYPE.get(source.type, ())
            if getattr(source, field) is not None
        }
        return ConnectorFactory.create_source_connector(
            source.type,
            host=source.host,
            port=source.port,
            database=source.database,
            username=source.username,
            password=password,
            **advanced,
        )

    async def test_connection(self, id: int) -> None:
        """Verify a source's stored credentials by opening a real connection.

        Raises:
            NotFoundError: If the source doesn't exist.
            ConnectionFailedError: If the connection attempt fails.
        """
        connector = await self.build_connector(id)
        async with connector:
            await connector.test_connection()

    async def get_tables(self, id: int) -> list[TableInfo]:
        """List the tables/views visible to a source's connection.

        Raises:
            NotFoundError: If the source doesn't exist.
            ConnectionFailedError: If the connection attempt fails.
        """
        connector = await self.build_connector(id)
        async with connector:
            return await connector.get_tables()

    async def get_table_schema(
        self, id: int, table_name: str, schema: str
    ) -> list[ColumnSchema]:
        """Describe the columns of one table/view on a source.

        Raises:
            NotFoundError: If the source doesn't exist.
            TableNotFoundError: If the table/view doesn't exist.
            ConnectionFailedError: If the connection attempt fails.
        """
        connector = await self.build_connector(id)
        async with connector:
            return await connector.get_table_schema(table_name, schema)

    async def preview_table(
        self,
        id: int,
        table_name: str,
        schema: str,
        columns: list[str] | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Fetch a small sample of rows from a source table, for preview
        while building a mapping.

        Raises:
            NotFoundError: If the source doesn't exist.
            TableNotFoundError: If the table/view doesn't exist.
            ConnectionFailedError: If the connection attempt fails.
        """
        connector = await self.build_connector(id)
        async with connector:
            return await connector.fetch_data(
                table_name, columns=columns, schema=schema, limit=limit
            )

    async def get(self, id: int) -> SourceRead:
        """Get a source by ID."""
        source = await self.repository.get_by_id(id)
        if not source:
            raise NotFoundError(f"Source with id {id} not found")
        return SourceRead.model_validate(source)

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
        name: str | None = None,
        type: str | None = None,
    ) -> SourceListResponse:
        """Get a paginated list of sources with optional filters."""
        total = await self.repository.get_count(name=name, type=type)
        items = await self.repository.get_all(
            skip=skip, limit=limit, name=name, type=type
        )
        return SourceListResponse(
            items=[SourceRead.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def create(self, data: SourceCreate) -> SourceRead:
        """Create a new source with unique name validation and password encryption."""
        existing = await self.repository.get_by_name(data.name)
        if existing:
            raise ConflictError(f"Source with name '{data.name}' already exists")

        # Encrypt password before storing
        encrypted = encrypt_password(data.password.get_secret_value())
        create_data = data.model_dump()
        create_data["password"] = encrypted

        source = await self.repository.create(SourceCreate(**create_data))
        return SourceRead.model_validate(source)

    async def update(self, id: int, data: SourceUpdate) -> SourceRead:
        """Update an existing source."""
        existing = await self.repository.get_by_id(id)
        if not existing:
            raise NotFoundError(f"Source with id {id} not found")

        # If name is being updated, check uniqueness
        if data.name and data.name != existing.name:
            name_exists = await self.repository.get_by_name(data.name)
            if name_exists:
                raise ConflictError(f"Source with name '{data.name}' already exists")

        # Encrypt password if provided
        update_dict = data.model_dump(exclude_unset=True)
        if "password" in update_dict and update_dict["password"] is not None:
            update_dict["password"] = encrypt_password(
                update_dict["password"].get_secret_value()
            )

        source = await self.repository.update(id, SourceUpdate(**update_dict))
        if not source:
            raise NotFoundError(f"Source with id {id} not found")
        return SourceRead.model_validate(source)

    async def delete(self, id: int) -> None:
        """Delete a source by ID."""
        deleted = await self.repository.delete(id)
        if not deleted:
            raise NotFoundError(f"Source with id {id} not found")

    async def get_decrypted_password(self, id: int) -> str:
        """Get decrypted password for a source (used internally by connectors)."""
        source = await self.repository.get_by_id(id)
        if not source:
            raise NotFoundError(f"Source with id {id} not found")
        return decrypt_password(source.password)
