"""
app/routers/accounts.py
────────────────────────
GET /api/v1/accounts      – list user's financial accounts
POST /api/v1/accounts     – add a new account
PATCH /api/v1/accounts/{id} – update account (name/balance/color)
DELETE /api/v1/accounts/{id} – delete account
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db
from app.models.account import Account
from app.repositories.account import AccountRepository
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/", response_model=list[AccountRead])
async def list_accounts(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return all accounts belonging to the authenticated user."""
    repo = AccountRepository(db)
    return await repo.list_by_user(user_id)


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Add a new bank, card, or cash account."""
    repo = AccountRepository(db)
    account = Account(user_id=user_id, **payload.model_dump())
    return await repo.create(account)


@router.patch("/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: UUID,
    payload: AccountUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = AccountRepository(db)
    account = await repo.get_user_account(account_id, user_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")
    return await repo.update(account, payload.model_dump(exclude_none=True))


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    repo = AccountRepository(db)
    account = await repo.get_user_account(account_id, user_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")
    await repo.delete(account)
