"""
Pydantic settings configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Attributes:
        DATABASE_URL: Async PostgreSQL connection string.
        DB_POOL_SIZE: Number of connections to keep in the pool.
        DB_MAX_OVERFLOW: Maximum overflow connections.
        SECRET_KEY: Secret key for JWT and session signing.
        ENCRYPTION_KEY: Fernet key for encrypting sensitive data (passwords).
        DEBUG: Enable debug mode (SQL echo, detailed errors).
        APP_NAME: Name of the application.
        APP_VERSION: Version string.
    """

    DATABASE_URL: str = "sqlite+aiosqlite:///./reverse_etl.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    SECRET_KEY: str
    ENCRYPTION_KEY: str

    DEBUG: bool = False
    APP_NAME: str = "Reverse ETL"
    APP_VERSION: str = "0.1.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore[call-arg]  # required fields come from env/.env
