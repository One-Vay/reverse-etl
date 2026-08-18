"""Unit tests for ConnectorFactory."""

import pytest

from app.connectors.destinations.amocrm import AmoCRMConnector
from app.connectors.destinations.bitrix24 import Bitrix24Connector
from app.connectors.factory import ConnectorFactory, UnknownConnectorTypeError
from app.connectors.sources.clickhouse import ClickHouseConnector
from app.connectors.sources.postgres import PostgresConnector

CONNECTION_PARAMS = {
    "host": "localhost",
    "port": 5432,
    "database": "db",
    "username": "user",
    "password": "pw",
}


class TestCreateSourceConnector:
    def test_creates_postgres_connector(self):
        connector = ConnectorFactory.create_source_connector(
            "postgres", **CONNECTION_PARAMS
        )
        assert isinstance(connector, PostgresConnector)

    def test_creates_clickhouse_connector(self):
        connector = ConnectorFactory.create_source_connector(
            "clickhouse", **CONNECTION_PARAMS
        )
        assert isinstance(connector, ClickHouseConnector)

    def test_accepts_str_subclass_enum_values(self):
        """SourceType is a `str` subclass — the factory shouldn't require a plain str."""

        class FakeSourceType(str):
            pass

        connector = ConnectorFactory.create_source_connector(
            FakeSourceType("postgres"), **CONNECTION_PARAMS
        )
        assert isinstance(connector, PostgresConnector)

    def test_unknown_type_raises_with_available_types_listed(self):
        with pytest.raises(UnknownConnectorTypeError, match="postgres"):
            ConnectorFactory.create_source_connector("mysql", **CONNECTION_PARAMS)


class TestCreateDestinationConnector:
    def test_creates_bitrix24_connector(self):
        connector = ConnectorFactory.create_destination_connector(
            "bitrix24", api_url="https://x.bitrix24.ru/rest/", auth_token="tok"
        )
        assert isinstance(connector, Bitrix24Connector)

    def test_creates_amocrm_connector(self):
        connector = ConnectorFactory.create_destination_connector(
            "amocrm", api_url="https://x.amocrm.ru/", auth_token="tok"
        )
        assert isinstance(connector, AmoCRMConnector)

    def test_unknown_type_raises_with_available_types_listed(self):
        with pytest.raises(UnknownConnectorTypeError, match="bitrix24"):
            ConnectorFactory.create_destination_connector("hubspot")
