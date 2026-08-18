"""Unit tests for AmoCRMConnector, with httpx fully mocked.

These tests never touch a real AmoCRM account — there's no free,
containerizable sandbox for it the way testcontainers gives Postgres/
ClickHouse, so this connector's correctness rests entirely on unit tests
against its documented REST contract (see the module docstring in
app/connectors/destinations/amocrm.py).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.connectors.base import (
    ConnectionFailedError,
    NotConnectedError,
    TableNotFoundError,
)
from app.connectors.destinations.amocrm import AmoCRMConnector


def make_connector(**overrides) -> AmoCRMConnector:
    params = {
        "api_url": "https://mycompany.amocrm.ru",
        "auth_token": "long-lived-token",
    }
    params.update(overrides)
    return AmoCRMConnector(**params)


def make_response(status_code=200, json_data=None) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.is_error = status_code >= 400
    response.text = str(json_data)
    response.json = MagicMock(return_value=json_data if json_data is not None else {})
    return response


def make_mock_client(account_response=None) -> MagicMock:
    client = MagicMock()
    client.request = AsyncMock(
        return_value=account_response or make_response(json_data={"id": 123})
    )
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def mock_async_client():
    client = make_mock_client()
    with patch(
        "app.connectors.destinations.amocrm.httpx.AsyncClient",
        MagicMock(return_value=client),
    ) as async_client_cls:
        yield async_client_cls, client


class TestConnect:
    @pytest.mark.asyncio
    async def test_builds_the_client_with_bearer_auth(self, mock_async_client):
        async_client_cls, _ = mock_async_client
        connector = make_connector(
            api_url="https://mycompany.amocrm.ru/", auth_token="secret-token"
        )

        await connector.connect()

        _, kwargs = async_client_cls.call_args
        assert kwargs["base_url"] == "https://mycompany.amocrm.ru/api/v4/"
        assert kwargs["headers"] == {"Authorization": "Bearer secret-token"}

    @pytest.mark.asyncio
    async def test_validates_credentials_with_an_account_call(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()

        await connector.connect()

        method, url = client.request.call_args.args
        assert method == "GET"
        assert url == "account"

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
    async def test_returns_the_standard_entities(self, mock_async_client):
        connector = make_connector()
        await connector.connect()

        entities = await connector.get_entities()

        assert entities == ["leads", "contacts", "companies", "tasks"]


class TestGetEntityFields:
    @pytest.mark.asyncio
    async def test_requires_an_active_connection(self):
        connector = make_connector()
        with pytest.raises(NotConnectedError):
            await connector.get_entity_fields("leads")

    @pytest.mark.asyncio
    async def test_includes_standard_fields(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(
            return_value=make_response(json_data={"_embedded": {"custom_fields": []}})
        )

        fields = await connector.get_entity_fields("leads")

        by_name = {f.name: f for f in fields}
        assert by_name["id"].is_primary_key is True
        assert by_name["name"].nullable is False
        assert "price" in by_name

    @pytest.mark.asyncio
    async def test_includes_discovered_custom_fields(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(
            return_value=make_response(
                json_data={
                    "_embedded": {
                        "custom_fields": [
                            {"field_id": 555, "type": "text", "is_required": True},
                            {"field_id": 556, "type": "numeric", "is_required": False},
                        ]
                    }
                }
            )
        )

        fields = await connector.get_entity_fields("contacts")

        by_name = {f.name: f for f in fields}
        assert by_name["custom_fields_values.555"].nullable is False
        assert by_name["custom_fields_values.556"].nullable is True

    @pytest.mark.asyncio
    async def test_tasks_have_no_custom_fields_call(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(return_value=make_response(json_data={}))

        fields = await connector.get_entity_fields("tasks")

        client.request.assert_not_called()
        assert {f.name for f in fields} == {
            "id",
            "text",
            "complete_till",
            "task_type_id",
            "responsible_user_id",
        }

    @pytest.mark.asyncio
    async def test_rejects_unknown_entity(self, mock_async_client):
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError):
            await connector.get_entity_fields("invoices")


class TestUpsertData:
    @pytest.mark.asyncio
    async def test_requires_an_active_connection(self):
        connector = make_connector()
        with pytest.raises(NotConnectedError):
            await connector.upsert_data("leads", [{"name": "New lead"}])

    @pytest.mark.asyncio
    async def test_rejects_unknown_entity(self, mock_async_client):
        connector = make_connector()
        await connector.connect()

        with pytest.raises(TableNotFoundError):
            await connector.upsert_data("invoices", [{"name": "x"}])

    @pytest.mark.asyncio
    async def test_creates_records_without_an_id(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(
            return_value=make_response(
                json_data={"_embedded": {"leads": [{"id": 1}, {"id": 2}]}}
            )
        )

        written = await connector.upsert_data(
            "leads", [{"name": "Lead A"}, {"name": "Lead B"}]
        )

        assert written == 2
        method, url = client.request.call_args.args
        assert method == "POST"
        assert url == "leads"
        assert client.request.call_args.kwargs["json"] == [
            {"name": "Lead A"},
            {"name": "Lead B"},
        ]

    @pytest.mark.asyncio
    async def test_updates_records_with_an_id(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(
            return_value=make_response(json_data={"_embedded": {"leads": [{"id": 7}]}})
        )

        written = await connector.upsert_data("leads", [{"id": 7, "name": "Updated"}])

        assert written == 1
        method, url = client.request.call_args.args
        assert method == "PATCH"
        assert url == "leads"

    @pytest.mark.asyncio
    async def test_splits_creates_and_updates_into_separate_calls(
        self, mock_async_client
    ):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        client.request = AsyncMock(
            side_effect=[
                make_response(json_data={"_embedded": {"leads": [{"id": 1}]}}),
                make_response(json_data={"_embedded": {"leads": [{"id": 7}]}}),
            ]
        )

        written = await connector.upsert_data(
            "leads", [{"name": "New"}, {"id": 7, "name": "Updated"}]
        )

        assert written == 2
        assert client.request.await_count == 2
        methods = {call.args[0] for call in client.request.call_args_list}
        assert methods == {"POST", "PATCH"}

    @pytest.mark.asyncio
    async def test_counts_only_records_returned_by_the_api(self, mock_async_client):
        _, client = mock_async_client
        connector = make_connector()
        await connector.connect()
        # AmoCRM returned only one of the two submitted records.
        client.request = AsyncMock(
            return_value=make_response(json_data={"_embedded": {"leads": [{"id": 1}]}})
        )

        written = await connector.upsert_data("leads", [{"name": "A"}, {"name": "B"}])

        assert written == 1
