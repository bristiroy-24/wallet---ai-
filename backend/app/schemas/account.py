"""app/schemas/account.py – Account DTOs"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.account import AccountType


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: AccountType = AccountType.BANK
    balance: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: str = Field(default="INR", max_length=3)
    color: str | None = Field(default=None, max_length=9)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    balance: Decimal | None = Field(default=None, ge=0)
    color: str | None = None


class AccountRead(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    type: AccountType
    balance: Decimal
    currency: str
    color: str | None

    model_config = {"from_attributes": True}
