"""Service layer for Destination entity."""

from app.connectors.base import ColumnSchema, DestinationConnector
from app.connectors.factory import ConnectorFactory
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import decrypt_password, encrypt_password
from app.features.destinations.repository import DestinationRepository
from app.features.destinations.schemas import (
    DestinationCreate,
    DestinationListResponse,
    DestinationRead,
    DestinationUpdate,
)


class DestinationService:
    """Business logic for destinations."""

    def __init__(self, repository: DestinationRepository):
        self.repository = repository

    async def _build_connector(self, id: int) -> DestinationConnector:
        """Look up a destination and build a connector for it, with its
        auth token decrypted. Raises NotFoundError if the destination
        doesn't exist; propagates UnknownConnectorTypeError from the
        factory if the destination's type has no connector registered."""
        destination = await self.repository.get_by_id(id)
        if not destination:
            raise NotFoundError(f"Destination with id {id} not found")

        auth_token = decrypt_password(destination.auth_token)
        return ConnectorFactory.create_destination_connector(
            destination.type,
            api_url=destination.api_url,
            auth_token=auth_token,
        )

    async def test_connection(self, id: int) -> None:
        """Verify a destination's stored credentials by opening a real
        connection.

        Raises:
            NotFoundError: If the destination doesn't exist.
            ConnectionFailedError: If the connection attempt fails.
        """
        connector = await self._build_connector(id)
        async with connector:
            await connector.test_connection()

    async def get_entities(self, id: int) -> list[str]:
        """List the entity types a destination can receive records as.

        Raises:
            NotFoundError: If the destination doesn't exist.
            ConnectionFailedError: If the connection attempt fails.
        """
        connector = await self._build_connector(id)
        async with connector:
            return await connector.get_entities()

    async def get_entity_fields(self, id: int, entity: str) -> list[ColumnSchema]:
        """Describe the fields available on one destination entity.

        Raises:
            NotFoundError: If the destination doesn't exist.
            TableNotFoundError: If the entity type doesn't exist.
            ConnectionFailedError: If the connection attempt fails.
        """
        connector = await self._build_connector(id)
        async with connector:
            return await connector.get_entity_fields(entity)

    async def get(self, id: int) -> DestinationRead:
        destination = await self.repository.get_by_id(id)
        if not destination:
            raise NotFoundError(f"Destination with id {id} not found")
        return DestinationRead.model_validate(destination)

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
        name: str | None = None,
        type: str | None = None,
    ) -> DestinationListResponse:
        total = await self.repository.get_count(name=name, type=type)
        items = await self.repository.get_all(
            skip=skip, limit=limit, name=name, type=type
        )
        return DestinationListResponse(
            items=[DestinationRead.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    async def create(self, data: DestinationCreate) -> DestinationRead:
        existing = await self.repository.get_by_name(data.name)
        if existing:
            raise ConflictError(f"Destination with name '{data.name}' already exists")

        # Encrypt auth_token
        encrypted = encrypt_password(data.auth_token.get_secret_value())
        create_data = data.model_dump()
        create_data["auth_token"] = encrypted

        destination = await self.repository.create(DestinationCreate(**create_data))
        return DestinationRead.model_validate(destination)

    async def update(self, id: int, data: DestinationUpdate) -> DestinationRead:
        existing = await self.repository.get_by_id(id)
        if not existing:
            raise NotFoundError(f"Destination with id {id} not found")

        if data.name and data.name != existing.name:
            name_exists = await self.repository.get_by_name(data.name)
            if name_exists:
                raise ConflictError(
                    f"Destination with name '{data.name}' already exists"
                )

        update_dict = data.model_dump(exclude_unset=True)
        if "auth_token" in update_dict and update_dict["auth_token"] is not None:
            update_dict["auth_token"] = encrypt_password(
                update_dict["auth_token"].get_secret_value()
            )

        destination = await self.repository.update(id, DestinationUpdate(**update_dict))
        if not destination:
            raise NotFoundError(f"Destination with id {id} not found")
        return DestinationRead.model_validate(destination)

    async def delete(self, id: int) -> None:
        deleted = await self.repository.delete(id)
        if not deleted:
            raise NotFoundError(f"Destination with id {id} not found")

    async def get_decrypted_token(self, id: int) -> str:
        destination = await self.repository.get_by_id(id)
        if not destination:
            raise NotFoundError(f"Destination with id {id} not found")
        return decrypt_password(destination.auth_token)
