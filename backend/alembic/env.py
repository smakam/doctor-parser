import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

# Load .env from backend/ directory so DATABASE_URL is available
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from alembic import context  # noqa: E402

from app.models.nameboard import Base  # noqa: E402

config = context.config
fileConfig(config.config_file_name)
target_metadata = Base.metadata

# Allow DATABASE_URL to be set via environment variable
database_url = os.environ.get("DATABASE_URL") or config.get_main_option(
    "sqlalchemy.url"
)
if database_url and database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    async def run_async_migrations():
        engine = create_async_engine(database_url)
        async with engine.begin() as conn:
            await conn.run_sync(do_run_migrations)
        await engine.dispose()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
