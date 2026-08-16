"""Service layer for Destination entity."""

from typing import Optional
from app.features.destinations.repository import DestinationRepository
from app.features.destinations.schemas import DestinationCreate, DestinationUpdate, DestinationRead, DestinationListResponse
from app.core.exceptions import NotFoundError, ConflictError
from app.core.security import encrypt_password, decrypt_password


class DestinationService:
    """Business logic for destinations."""

    def __init__(self, repository: DestinationRepository):
        self.repository = repository

    async def get(self, id: int) -> DestinationRead:
        destination = await self.repository.get_by_id(id)
        if not destination:
            raise NotFoundError(f"Destination with id {id} not found")
        return DestinationRead.model_validate(destination)

    async def get_list(
        self,
        skip: int = 0,
        limit: int = 100,
        name: Optional[str] = None,
        type: Optional[str] = None,
    ) -> DestinationListResponse:
        total = await self.repository.get_count(name=name, type=type)
        items = await self.repository.get_all(skip=skip, limit=limit, name=name, type=type)
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
                raise ConflictError(f"Destination with name '{data.name}' already exists")

        update_dict = data.model_dump(exclude_unset=True)
        if "auth_token" in update_dict and update_dict["auth_token"] is not None:
            update_dict["auth_token"] = encrypt_password(update_dict["auth_token"].get_secret_value())

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