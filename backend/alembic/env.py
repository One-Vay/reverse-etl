import sys
from logging.config import fileConfig
from pathlib import Path
from urllib.parse import urlparse

from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import Base

# Import every model module so their tables register on Base.metadata before
# autogenerate compares it against the database. Without these imports,
# Base.metadata is empty and autogenerate thinks all existing tables should
# be dropped.
from app.features.destinations import models as destinations_models  # noqa: F401
from app.features.mappings import models as mappings_models  # noqa: F401
from app.features.settings import models as settings_models  # noqa: F401
from app.features.sources import models as sources_models  # noqa: F401
from app.features.syncs import models as syncs_models  # noqa: F401

config = context.config
# Alembic runs migrations synchronously, so swap the async drivers used by the
# application (asyncpg / aiosqlite) for their sync counterparts.
database_url = settings.DATABASE_URL
if "postgresql+asyncpg://" in database_url:
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
elif "sqlite+aiosqlite://" in database_url:
    database_url = database_url.replace("sqlite+aiosqlite://", "sqlite://")
config.set_main_option("sqlalchemy.url", database_url)
fileConfig(config.config_file_name)

target_metadata = Base.metadata


def ensure_database_exists():
    """Создаёт базу данных, если она не существует."""
    target_url = settings.DATABASE_URL
    parsed = urlparse(target_url)
    db_name = parsed.path.lstrip("/")
    if parsed.scheme.startswith("postgresql"):
        # Используем синхронный драйвер для проверки/создания БД
        sync_url = target_url.replace("postgresql+asyncpg://", "postgresql://")
        base_url = sync_url.replace(f"/{db_name}", "/postgres")
        try:
            engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            engine_default = create_engine(base_url, isolation_level="AUTOCOMMIT")
            with engine_default.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {db_name}"))
            print(f"✅ База данных '{db_name}' создана.")
    elif "sqlite" in parsed.scheme:
        pass  # SQLite создаёт файл автоматически


ensure_database_exists()


def run_migrations_offline():
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    # Используем синхронный движок (psycopg2)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
