"""Unit tests for the not-yet-implemented connector stubs.

These just pin down the contract: every abstract method fails loudly and
clearly rather than silently doing nothing or crashing with a confusing
low-level error.
"""

import pytest

from app.connectors.destinations.amocrm import AmoCRMConnector
from app.connectors.destinations.bitrix24 import Bitrix24Connector

DESTINATION_STUBS = [Bitrix24Connector, AmoCRMConnector]


@pytest.mark.parametrize("connector_cls", DESTINATION_STUBS)
class TestDestinationConnectorStubs:
    @pytest.mark.asyncio
    async def test_connect_raises_not_implemented(self, connector_cls):
        with pytest.raises(NotImplementedError):
            await connector_cls().connect()

    @pytest.mark.asyncio
    async def test_disconnect_is_a_safe_noop(self, connector_cls):
        await connector_cls().disconnect()  # must not raise

    @pytest.mark.asyncio
    async def test_get_entities_raises_not_implemented(self, connector_cls):
        with pytest.raises(NotImplementedError):
            await connector_cls().get_entities()

    @pytest.mark.asyncio
    async def test_get_entity_fields_raises_not_implemented(self, connector_cls):
        with pytest.raises(NotImplementedError):
            await connector_cls().get_entity_fields("leads")

    @pytest.mark.asyncio
    async def test_upsert_data_raises_not_implemented(self, connector_cls):
        with pytest.raises(NotImplementedError):
            await connector_cls().upsert_data("leads", [{"name": "Jane"}])
