"""Factory for constructing connectors by type name.

This is the only place in the connector layer that knows about *every*
concrete connector. Adding a new connector means writing the class and
adding one line to a registry dict here — nothing else in the app needs
to change, since callers only ever ask the factory for "a source
connector for type X", never import a concrete connector class directly.
"""

from app.connectors.base import DestinationConnector, SourceConnector
from app.connectors.destinations.amocrm import AmoCRMConnector
from app.connectors.destinations.bitrix24 import Bitrix24Connector
from app.connectors.sources.clickhouse import ClickHouseConnector
from app.connectors.sources.postgres import PostgresConnector


class UnknownConnectorTypeError(Exception):
    """Raised when no connector is registered for a requested type name."""


class ConnectorFactory:
    """Looks up and instantiates connectors by their type name.

    Type names are plain strings (e.g. `"postgres"`, `"bitrix24"`) rather
    than the app's `SourceType`/`DestinationType` enums, so this module
    has no dependency on `app.features`. Since those enums are `str`
    subclasses, passing an enum member in directly also works.
    """

    _source_registry: dict[str, type[SourceConnector]] = {
        "postgres": PostgresConnector,
        "clickhouse": ClickHouseConnector,
    }

    _destination_registry: dict[str, type[DestinationConnector]] = {
        "bitrix24": Bitrix24Connector,
        "amocrm": AmoCRMConnector,
    }

    @classmethod
    def create_source_connector(
        cls, connector_type: str, **connection_params: object
    ) -> SourceConnector:
        """Instantiate a source connector for `connector_type`.

        Args:
            connector_type: e.g. `"postgres"`.
            **connection_params: Forwarded to the connector's constructor
                (typically `host`, `port`, `database`, `username`, `password`).

        Raises:
            UnknownConnectorTypeError: If no source connector is registered
                for `connector_type`.
        """
        connector_cls = cls._source_registry.get(str(connector_type))
        if connector_cls is None:
            raise UnknownConnectorTypeError(
                f"No source connector registered for type '{connector_type}'. "
                f"Available types: {', '.join(sorted(cls._source_registry))}."
            )
        return connector_cls(**connection_params)

    @classmethod
    def create_destination_connector(
        cls, connector_type: str, **connection_params: object
    ) -> DestinationConnector:
        """Instantiate a destination connector for `connector_type`.

        Args:
            connector_type: e.g. `"bitrix24"`.
            **connection_params: Forwarded to the connector's constructor.

        Raises:
            UnknownConnectorTypeError: If no destination connector is
                registered for `connector_type`.
        """
        connector_cls = cls._destination_registry.get(str(connector_type))
        if connector_cls is None:
            raise UnknownConnectorTypeError(
                f"No destination connector registered for type '{connector_type}'. "
                f"Available types: {', '.join(sorted(cls._destination_registry))}."
            )
        return connector_cls(**connection_params)
