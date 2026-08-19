"""Unit tests for Bitrix24Connector, with httpx fully mocked.

These tests never touch a real Bitrix24 portal — there's no free,
containerizable sandbox for it the way testcontainers gives Postgres/
ClickHouse, so this connector's correctness rests entirely on unit tests
against its documented REST contract (see the module docstring in
app/connectors/destinations/bitrix24.py).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.connectors.base import (
    ConnectionFailedError,
    NotConnectedError,
    TableNotFoundError,
)
from app.connectors.destinations.bitrix24 import Bitrix24Connector


def make_connector(**overrides) -> Bitrix24Connector:
    params = {
        "api_url": "https://mycompany.bitrix24.ru",
        "auth_token": "1/webhooksecret",
    }
    params.update(overrides)
    return Bitrix24Connector(**params)


def make_response(status_code=200, json_data=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.is_error = status_code >= 400
    response.text = str(json_data)
    response.json = MagicMock(return_value=json_data if json_data is not None else {})
    return response


def make_mock_client(profile_response=None) -> MagicMock:
    client = MagicMock()
    client.request = AsyncMock(
        return_value=profile_response or make_response(json_data={"result": {"ID": 1}})
    )
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_async_client():
    client = make_mock_client()
    with patch(
        "app.connectors.destinations.bitrix24.httpx.AsyncClient",
        MagicMock(return_value=client),
    ) as async_client_cls:
        yield async_client_cls, client


class TestConnect:
    @pytest.mark.asyncio
    async def test_builds_the_client_with_the_webhook_base_url(self, mock_async_client):
        async_client_cls, _ = mock_async_client
        connector = make_connector(
            api_url="https://mycompany.bitrix24.ru/", auth_token="/1/secret/"
        )

        await connector.connect()

        _, kwargs = async_client_cls.call_args
        assert kwargs["base_url"] == "https://mycompany.bitrix24.ru/rest/1/secret/"

    @pytest.mark.asyncio
    async def test_validates_credentials_with_a_profile_call(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()

        await connector.connect()

        client.request.assert_awaited_once()
        method, url = client.request.call_args.args
        assert method == "POST"
        assert url == "profile"

    @pytest.mark.asyncio
    async def test_is_idempotent(self, mock_async_client):
        async_client_cls, _ = mock_async_client
        connector = make_connector()

        await connector.connect()
        await connector.connect()

        async_client_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_network_failure_raises_connection_failed(self, mock_async_client):
        _, client = mock_async_client
        client.request = AsyncMock(side_effect=httpx.ConnectTimeout("timed out"))
        connector = make_connector()

        with pytest.raises(ConnectionFailedError):
            await connector.connect()

    @pytest.mark.asyncio
    async def test_http_401_raises_connection_failed(self, mock_async_client):
        _, client = mock_async_client
        client.request = AsyncMock(return_value=make_response(status_code=401))
        connector = make_connector()

        with pytest.raises(ConnectionFailedError):
            await connector.connect()

    @pytest.mark.asyncio
    async def test_bitrix_error_body_raises_connection_failed(self, mock_async_client):
        _, client = mock_async_client
        client.request = AsyncMock(
            return_value=make_response(
                json_data={
                    "error": "INVALID_TOKEN",
                    "error_description": "Webhook not found",
                }
            )
        )
        connector = make_connector()

        with pytest.raises(ConnectionFailedError, match="Webhook not found"):
            await connector.connect()

    @pytest.mark.asyncio
    async def test_failed_connect_closes_the_client(self, mock_async_client):
        _, client = mock_async_client
        client.request = AsyncMock(side_effect=httpx.ConnectTimeout("timed out"))
        connector = make_connector()

        with pytest.raises(ConnectionFailedError):
            await connector.connect()

        client.aclose.assert_awaited_once()


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_closes_the_client(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()

        await connector.disconnect()

        client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_is_a_noop_when_never_connected(self):
        connector = make_connector()
        await connector.disconnect()  # must not raise

    @pytest.mark.asyncio
    async def test_context_manager_connects_and_disconnects(self, mock_async_client):
        async_client_cls, client = mock_async_client
        connector = make_connector()

        async with connector as ctx:
            assert ctx is connector
            async_client_cls.assert_called_once()

        client.aclose.assert_awaited_once()


class TestTestConnection:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self, mock_async_client):
        connector = make_connector()
        assert await connector.test_connection() is True

    @pytest.mark.asyncio
    async def test_closes_client_it_opened_for_itself(self, mock_async_client):
        connector = make_connector()
        await connector.test_connection()
        assert connector._client is None

    @pytest.mark.asyncio
    async def test_leaves_an_already_open_client_connected(self, mock_async_client):
        connector = make_connector()
        await connector.connect()

        await connector.test_connection()

        assert connector._client is not None


class TestGetEntities:
    @pytest.mark.asyncio
    async def test_requires_an_active_connection(self):
        connector = make_connector()
        with pytest.raises(NotConnectedError):
            await connector.get_entities()

    @pytest.mark.asyncio
    async def test_returns_the_standard_crm_entities(self, mock_async_client):
        connector = make_connector()
        await connector.connect()

        entities = await connector.get_entities()

        assert entities == ["lead", "contact", "company", "deal"]


class TestGetEntityFields:
    @pytest.mark.asyncio
    async def test_requires_an_active_connection(self):
        connector = make_connector()
        with pytest.raises(NotConnectedError):
            await connector.get_entity_fields("lead")

    @pytest.mark.asyncio
    async def test_maps_bitrix_field_metadata_to_column_schema(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()

        client.request = AsyncMock(
            return_value=make_response(
                json_data={
                    "result": {
                        "ID": {"type": "integer", "isRequired": "Y"},
                        "TITLE": {"type": "string", "isRequired": "Y"},
                        "OPENED": {"type": "char", "isRequired": "N"},
                    }
                }
            )
        )

        fields = await connector.get_entity_fields("lead")

        by_name = {f.name: f for f in fields}
        assert by_name["ID"].is_primary_key is True
        assert by_name["ID"].nullable is False
        assert by_name["TITLE"].data_type == "string"
        assert by_name["OPENED"].nullable is True

    @pytest.mark.asyncio
    async def test_calls_the_fields_method_for_the_requested_entity(
        self, mock_async_client
    ):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(return_value=make_response(json_data={"result": {}}))

        await connector.get_entity_fields("deal")

        method, url = client.request.call_args.args
        assert url == "crm.deal.fields"

    @pytest.mark.asyncio
    async def test_rejects_unknown_entity(self, mock_async_client):
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError):
            await connector.get_entity_fields("invoice")


class TestUpsertData:
    @pytest.mark.asyncio
    async def test_requires_an_active_connection(self):
        connector = make_connector()
        with pytest.raises(NotConnectedError):
            await connector.upsert_data("lead", [{"TITLE": "New lead"}])

    @pytest.mark.asyncio
    async def test_rejects_unknown_entity(self, mock_async_client):
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError):
            await connector.upsert_data("invoice", [{"TITLE": "x"}])

    @pytest.mark.asyncio
    async def test_creates_records_without_an_id(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(return_value=make_response(json_data={"result": 42}))

        written = await connector.upsert_data("lead", [{"TITLE": "New lead"}])

        assert written == 1
        method, url = client.request.call_args.args
        assert url == "crm.lead.add"
        assert client.request.call_args.kwargs["json"] == {
            "fields": {"TITLE": "New lead"}
        }

    @pytest.mark.asyncio
    async def test_wraps_plain_values_for_multifield_codes(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(return_value=make_response(json_data={"result": 1}))

        await connector.upsert_data(
            "lead",
            [{"TITLE": "New lead", "PHONE": "+7 999 000-00-00", "EMAIL": "a@b.ru"}],
        )

        sent_fields = client.request.call_args.kwargs["json"]["fields"]
        assert sent_fields["TITLE"] == "New lead"
        assert sent_fields["PHONE"] == [
            {"VALUE": "+7 999 000-00-00", "VALUE_TYPE": "WORK"}
        ]
        assert sent_fields["EMAIL"] == [{"VALUE": "a@b.ru", "VALUE_TYPE": "WORK"}]

    @pytest.mark.asyncio
    async def test_does_not_double_wrap_an_already_structured_multifield(
        self, mock_async_client
    ):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(return_value=make_response(json_data={"result": 1}))

        already_wrapped = [{"VALUE": "+7 999 000-00-00", "VALUE_TYPE": "MOBILE"}]
        await connector.upsert_data("lead", [{"PHONE": already_wrapped}])

        sent_fields = client.request.call_args.kwargs["json"]["fields"]
        assert sent_fields["PHONE"] == already_wrapped

    @pytest.mark.asyncio
    async def test_leaves_none_multifield_values_untouched(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(return_value=make_response(json_data={"result": 1}))

        await connector.upsert_data("lead", [{"TITLE": "x", "PHONE": None}])

        sent_fields = client.request.call_args.kwargs["json"]["fields"]
        assert sent_fields["PHONE"] is None

    @pytest.mark.asyncio
    async def test_updates_records_with_an_id(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(
            return_value=make_response(json_data={"result": True})
        )

        written = await connector.upsert_data(
            "lead", [{"ID": 7, "TITLE": "Updated lead"}]
        )

        assert written == 1
        method, url = client.request.call_args.args
        assert url == "crm.lead.update"
        assert client.request.call_args.kwargs["json"] == {
            "id": 7,
            "fields": {"TITLE": "Updated lead"},
        }

    @pytest.mark.asyncio
    async def test_counts_only_successful_records(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(
            side_effect=[
                make_response(json_data={"result": 1}),
                make_response(
                    json_data={
                        "error": "NOT_FOUND",
                        "error_description": "Lead not found",
                    }
                ),
            ]
        )

        written = await connector.upsert_data(
            "lead",
            [{"TITLE": "ok"}, {"ID": 999, "TITLE": "missing"}],
        )

        assert written == 1
