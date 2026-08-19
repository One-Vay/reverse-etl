"""Repository for the singleton AppSettings row."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.settings.models import SINGLETON_ID, AppSettings
from app.features.settings.schemas import AppSettingsUpdate


class SettingsRepository:
    """Get-or-create access to the one `AppSettings` row."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self) -> AppSettings:
        """Return the singleton settings row, creating it with defaults on
        first access — avoids needing a separate seed migration."""
        stmt = select(AppSettings).where(AppSettings.id == SINGLETON_ID)
        result = await self.session.execute(stmt)
        settings = result.scalar_one_or_none()
        if settings is not None:
            return settings

        settings = AppSettings(id=SINGLETON_ID)
        self.session.add(settings)
        await self.session.flush()
        return settings

    async def update(self, data: AppSettingsUpdate) -> AppSettings:
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            return await self.get()

        # Ensure the row exists before updating it.
        await self.get()

        stmt = (
            update(AppSettings)
            .where(AppSettings.id == SINGLETON_ID)
            .values(**update_dict)
            .returning(AppSettings)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        settings = result.scalar_one()
        return settings
