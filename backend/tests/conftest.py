"""
tests/conftest.py
──────────────────
Shared pytest fixtures for the WalletAI test suite.

Strategy:
  - In-memory SQLite via aiosqlite (no PostgreSQL required).
  - Transaction.tags column patched from PostgreSQL ARRAY → Text before
    any create_all(), because SQLite doesn't support ARRAY.
  - FastAPI app tested via httpx.AsyncClient + ASGI transport.
  - Rate limiting completely disabled: the Limiter.hit() method is
    monkey-patched to always return True (within limits).
  - AI service always MockAIService.
"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.core.dependencies import get_db
from app.db.base import Base
from app.main import create_app
from app.services.ai_factory import AIFactory

# ── Patch PostgreSQL ARRAY → Text for SQLite compatibility ────────────────────
from app.models.transaction import Transaction
Transaction.__table__.c.tags.type = Text()

# ── In-memory SQLite ──────────────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


# ── Create tables once per session ───────────────────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Rolled-back session per test ─────────────────────────────────────────────
@pytest_asyncio.fixture(autouse=True)
async def db_session():
    """Each test runs in a transaction that is rolled back at teardown."""
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()


# ── Test HTTP client ──────────────────────────────────────────────────────────
@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """
    FastAPI test client with:
      - DB injected as the rolled-back test session
      - MockAIService always used
      - Rate limiter disabled (hit() always returns True = within limits)
    """
    AIFactory.reset()
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Disable slowapi rate limiting: patch the storage backend's get/incr
    # so every request appears as count=0 (never throttled).
    with patch("limits.storage.MemoryStorage.incr", return_value=1), \
         patch("limits.storage.MemoryStorage.get",  return_value=0):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac

    app.dependency_overrides.clear()
