"""
app/routers/auth.py
────────────────────
User registration and login endpoints.

Rate limits (brute-force protection):
  - POST /login    → 10 requests / minute per IP
  - POST /register → 5  requests / minute per IP
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(
    request: Request,           # required by slowapi to extract client IP
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user account.
    Rate limited to 5 registrations per minute per IP.
    """
    repo = UserRepository(db)

    if await repo.get_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    created = await repo.create(user)
    return created


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,           # required by slowapi to extract client IP
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate and receive a JWT access token.
    Rate limited to 10 attempts per minute per IP to prevent brute-force.
    """
    repo = UserRepository(db)
    user = await repo.get_by_email(payload.email)

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is disabled.",
        )

    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))
