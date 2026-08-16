"""
app/db/session.py
──────────────────
Async SQLAlchemy engine and session factory.

The engine is created once at import time and reused for the
life of the process (connection pool). Session objects are
short-lived and scoped to a single request via get_db().
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # logs SQL in development
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,            # checks connection health before use
)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,        # objects remain usable after commit
    autoflush=False,
)


async def create_all_tables() -> None:
    """
    Helper used only for development / testing when Alembic is not set up.
    In production, always use Alembic migrations.
    """
    from app.db.base import Base  # local import to avoid circular

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
