"""
app/core/dependencies.py
─────────────────────────
FastAPI dependency injection helpers.

All routers import from here to stay decoupled from
infrastructure concerns (DB sessions, auth, AI service).
"""

from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal
from app.services.ai_factory import AIFactory, BaseAIService

bearer_scheme = HTTPBearer(auto_error=False)


# ── Database Session ──────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator:
    """
    Yields an async SQLAlchemy session scoped to the request lifetime.
    Always commits on success, rolls back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Authentication ────────────────────────────────────────────────────────────

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UUID:
    """
    Validates the Bearer JWT token and returns the authenticated user's UUID.
    Raises HTTP 401 if the token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id_str = decode_access_token(credentials.credentials)
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )


# ── AI Service ────────────────────────────────────────────────────────────────

def get_ai_service(
    settings: Settings = Depends(get_settings),
) -> BaseAIService:
    """
    Returns the appropriate AI service implementation based on settings.
    Uses AIFactory (Factory Pattern) to select between GeminiAIService
    and MockAIService without the router knowing which one it gets.
    """
    return AIFactory.create(settings)
