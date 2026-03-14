from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# when using SQLite in-memory during tests the pool options trigger errors
# so we only pass them for non-SQLite URLs
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": settings.DEBUG,
}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({"pool_size": 10, "max_overflow": 20})

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables on startup (dev only — use Alembic in prod)."""
    # When running locally without a DB server (e.g. just spinning up the
    # frontend or running quick manual tests), we don't want the whole app to
    # crash if Postgres isn't available. Catch connection errors and log a
    # warning so the server can still start.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # pragma: no cover - hard to trigger in ci
        import logging

        logging.warning(f"init_db failed, database may be unreachable: {exc}")
        # don't re-raise; some endpoints will still fail later when the DB is
        # actually used, but the process won't bail at startup.


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
