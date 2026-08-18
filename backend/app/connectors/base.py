"""Abstract interfaces every connector must implement.

Two symmetric contracts are defined here:

- `SourceConnector` — read-only access to a data source (a database, an
  API, a file store...). Used to browse its schema and pull rows.
- `DestinationConnector` — write access to a destination system (a CRM,
  a warehouse...). Used to discover its entities/fields and push rows.

Both are async context managers, so callers can write:

    async with connector:
        tables = await connector.get_tables()

and be guaranteed `disconnect()` runs even if an exception is raised.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal


class ConnectorError(Exception):
    """Base class for all errors raised by connectors."""


class ConnectionFailedError(ConnectorError):
    """The connector could not establish or authenticate a connection.

    Callers should treat the exception message as safe to show to an end
    user — connector implementations are expected to translate low-level
    driver errors into a clear, actionable sentence.
    """


class TableNotFoundError(ConnectorError):
    """A requested table, view, or entity does not exist on the remote system."""


class NotConnectedError(ConnectorError):
    """A connector method that requires an active connection was called
    before `connect()` (or after `disconnect()`)."""


@dataclass(frozen=True, slots=True)
class TableInfo:
    """One queryable table or view on a source system.

    Attributes:
        name: Table/view name, unqualified.
        schema: Schema (or namespace/database) the table lives in.
        kind: Either `"table"` or `"view"`.
    """

    name: str
    schema: str
    kind: Literal["table", "view"] = "table"


@dataclass(frozen=True, slots=True)
class ColumnSchema:
    """One column of a table, view, or destination entity.

    Attributes:
        name: Column name.
        data_type: The remote system's own type name (e.g. `"integer"`,
            `"character varying"`) — deliberately not normalized to a
            shared type system, since callers generally just display it.
        nullable: Whether the column accepts NULL.
        is_primary_key: Whether the column is (part of) the primary key.
    """

    name: str
    data_type: str
    nullable: bool
    is_primary_key: bool = False


class SourceConnector(ABC):
    """Read-only connector to a data source.

    Implementations are expected to be constructed with whatever
    connection parameters they need (host, port, credentials, ...) and to
    defer actually opening a connection until `connect()` is called.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Open the underlying connection (e.g. a pool).

        Must be safe to call more than once — a second call while already
        connected should be a no-op rather than raising.

        Raises:
            ConnectionFailedError: If the connection or authentication
                fails. The message must be safe to show to an end user.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the underlying connection and release its resources.

        Must be safe to call even if `connect()` was never called, or was
        already followed by a `disconnect()`.
        """

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify connectivity and credentials with a cheap round-trip.

        Returns:
            `True` if the connection is usable.

        Raises:
            ConnectionFailedError: If the round-trip fails. Implementations
                should raise rather than return `False`, so the caller gets
                a message explaining *why* it failed.
        """

    @abstractmethod
    async def get_tables(self) -> list[TableInfo]:
        """List every table and view visible to the configured credentials.

        Returns:
            One `TableInfo` per table/view. Order is implementation-defined
            but should be stable (e.g. alphabetical) for a pleasant UI.

        Raises:
            ConnectionFailedError: If not connected and connecting fails.
        """

    @abstractmethod
    async def get_table_schema(
        self, table_name: str, schema: str | None = None
    ) -> list[ColumnSchema]:
        """Describe the columns of a single table or view.

        Args:
            table_name: Unqualified table/view name.
            schema: Schema/namespace the table lives in. Connectors that
                have no notion of schema may ignore this.

        Returns:
            One `ColumnSchema` per column, in the source's natural
            (typically ordinal) order.

        Raises:
            TableNotFoundError: If the table/view does not exist.
            ConnectionFailedError: If not connected and connecting fails.
        """

    @abstractmethod
    async def fetch_data(
        self,
        table_name: str,
        columns: list[str] | None = None,
        schema: str | None = None,
        limit: int | None = None,
        where: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read rows from a table or view.

        Args:
            table_name: Unqualified table/view name.
            columns: Columns to select; `None` selects all columns.
            schema: Schema/namespace the table lives in.
            limit: Maximum number of rows to return; `None` for no limit.
            where: A raw boolean SQL expression appended to the query's
                `WHERE` clause (e.g. `"updated_at > '2024-01-01'"`). This
                is interpolated as literal SQL, not a bound parameter —
                only pass expressions from trusted, internal callers, never
                directly from an unauthenticated HTTP request.

        Returns:
            One `dict` per row, mapping column name to value.

        Raises:
            TableNotFoundError: If the table/view does not exist.
            ConnectionFailedError: If not connected and connecting fails.
        """

    async def __aenter__(self) -> "SourceConnector":
        await self.connect()
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.disconnect()


class DestinationConnector(ABC):
    """Write-capable connector to a destination system."""

    @abstractmethod
    async def connect(self) -> None:
        """Open the underlying connection.

        Raises:
            ConnectionFailedError: If the connection or authentication
                fails. The message must be safe to show to an end user.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the underlying connection and release its resources."""

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify connectivity and credentials with a cheap round-trip.

        Returns:
            `True` if the connection is usable.

        Raises:
            ConnectionFailedError: If the round-trip fails.
        """

    @abstractmethod
    async def get_entities(self) -> list[str]:
        """List the entity types this destination can receive records as
        (e.g. `"leads"`, `"contacts"`).

        Raises:
            ConnectionFailedError: If not connected and connecting fails.
        """

    @abstractmethod
    async def get_entity_fields(self, entity: str) -> list[ColumnSchema]:
        """Describe the fields available on a destination entity.

        Args:
            entity: One of the values returned by `get_entities()`.

        Raises:
            TableNotFoundError: If the entity type does not exist.
            ConnectionFailedError: If not connected and connecting fails.
        """

    @abstractmethod
    async def upsert_data(self, entity: str, records: list[dict[str, Any]]) -> int:
        """Create or update records of the given entity type.

        Args:
            entity: One of the values returned by `get_entities()`.
            records: Field-name-to-value mappings to write. Matching an
                existing record (update vs. create) is destination-specific.

        Returns:
            Number of records successfully written.

        Raises:
            TableNotFoundError: If the entity type does not exist.
            ConnectionFailedError: If not connected and connecting fails.
        """

    async def __aenter__(self) -> "DestinationConnector":
        await self.connect()
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.disconnect()
