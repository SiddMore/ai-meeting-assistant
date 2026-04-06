import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import all models so Alembic can detect them
from app.db.base import Base  # noqa: F401
from app.core.config import settings

config = context.config

# ── RENDER URL FIX ───────────────────────────────────────────────────────────
# Function to ensure URL is compatible with asyncpg
def get_url():
    url = settings.DATABASE_URL
    if url.startswith("postgres://"):
        # Render gives postgres://, but asyncpg needs postgresql+asyncpg://
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

# Set the URL for Alembic
config.set_main_option("sqlalchemy.url", get_url())

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """The sync migration execution."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an engine and run migrations async."""
    # We use the cleaned-up URL here
    connectable = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Note: If called from within an existing event loop (like FastAPI lifespan),
    # this may need a different approach. We handle that in main.py.
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If we're already in a loop, we can't use asyncio.run()
        # The calling code in main.py should handle this via a thread.
        import nest_asyncio
        nest_asyncio.apply()
        loop.run_until_complete(run_async_migrations())
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()