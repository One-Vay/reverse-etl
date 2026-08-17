"""Pytest fixtures with mocks for testing."""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.features.sources.repository import SourceRepository
from app.features.sources.service import SourceService
from app.features.destinations.repository import DestinationRepository
from app.features.destinations.service import DestinationService
from app.features.mappings.repository import MappingRepository
from app.features.mappings.service import MappingService
from app.features.syncs.repository import SyncRepository
from app.features.syncs.service import SyncService
from app.features.sources.router import get_source_service
from app.features.destinations.router import get_destination_service
from app.features.mappings.router import get_mapping_service
from app.features.syncs.router import get_sync_service


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def source_repository(mock_db_session):
    repo = MagicMock(spec=SourceRepository)
    repo.session = mock_db_session
    return repo


@pytest.fixture
def destination_repository(mock_db_session):
    repo = MagicMock(spec=DestinationRepository)
    repo.session = mock_db_session
    return repo


@pytest.fixture
def mapping_repository(mock_db_session):
    repo = MagicMock(spec=MappingRepository)
    repo.session = mock_db_session
    return repo


@pytest.fixture
def sync_repository(mock_db_session):
    repo = MagicMock(spec=SyncRepository)
    repo.session = mock_db_session
    return repo


@pytest.fixture
def source_service(source_repository):
    service = MagicMock(spec=SourceService)
    service.repository = source_repository
    return service


@pytest.fixture
def destination_service(destination_repository):
    service = MagicMock(spec=DestinationService)
    service.repository = destination_repository
    return service


@pytest.fixture
def mapping_service(mapping_repository, source_repository):
    service = MagicMock(spec=MappingService)
    service.repository = mapping_repository
    service.source_repository = source_repository
    return service


@pytest.fixture
def sync_service(
    sync_repository, source_repository, destination_repository, mapping_repository
):
    service = MagicMock(spec=SyncService)
    service.repository = sync_repository
    service.source_repository = source_repository
    service.destination_repository = destination_repository
    service.mapping_repository = mapping_repository
    return service


@pytest_asyncio.fixture
async def client(
    source_service, destination_service, mapping_service, sync_service, mock_db_session
):
    """Create test client with overridden dependencies."""

    def override_get_source_service():
        return source_service

    def override_get_destination_service():
        return destination_service

    def override_get_mapping_service():
        return mapping_service

    def override_get_sync_service():
        return sync_service

    app.dependency_overrides[get_source_service] = override_get_source_service
    app.dependency_overrides[get_destination_service] = override_get_destination_service
    app.dependency_overrides[get_mapping_service] = override_get_mapping_service
    app.dependency_overrides[get_sync_service] = override_get_sync_service
    app.dependency_overrides[get_db] = lambda: mock_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    return "asyncio"
