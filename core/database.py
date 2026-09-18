from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings

# asyncpg connect args for Supabase / PgBouncer compatibility
connect_args = {}
if "postgresql" in settings.async_database_url:
    # statement_cache_size=0 required for Supabase Transaction pooler
    connect_args["statement_cache_size"] = 0
    # Reduce connection overhead
    connect_args["server_settings"] = {
        "application_name": "esavdo_bot",
        "jit": "off",  # Disable JIT for short queries - faster response
    }

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.DEBUG,
    pool_pre_ping=False,   # Skip pre-ping: reduces latency per request
    pool_size=15,          # More concurrent connections
    max_overflow=25,
    pool_recycle=1800,     # Recycle connections every 30 min
    pool_timeout=10,       # Fail fast if no connection available
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autobegin=True,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
