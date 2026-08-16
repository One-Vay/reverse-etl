"""Service layer for Source entity."""

from typing import Optional, Sequence
from app.features.sources.repository import SourceRepository
from app.features.sources.schemas import SourceCreate, SourceUpdate, SourceRead, SourceListResponse
from app.core.exceptions import NotFoundError, ConflictError
from app.core.security import encrypt_password, decrypt_password


class SourceService:
    """Business logic for sources."""

    def __init__(self, repository: SourceRepository):
        self.repository = repository

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
        name: Optional[str] = None,
        type: Optional[str] = None,
    ) -> SourceListResponse:
        """Get a paginated list of sources with optional filters."""
        total = await self.repository.get_count(name=name, type=type)
        items = await self.repository.get_all(skip=skip, limit=limit, name=name, type=type)
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
            update_dict["password"] = encrypt_password(update_dict["password"].get_secret_value())

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