"""app/schemas/transaction.py – Transaction DTOs"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.transaction import TransactionType


class TransactionCreate(BaseModel):
    account_id: UUID | None = None
    category_id: UUID | None = None
    amount: Decimal = Field(gt=0)
    type: TransactionType = TransactionType.EXPENSE
    note: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list)
    date: datetime | None = None


class TransactionRead(BaseModel):
    id: UUID
    user_id: UUID
    account_id: UUID | None
    category_id: UUID | None
    amount: Decimal
    type: TransactionType
    note: str | None
    tags: list[str]
    date: datetime
    created_at: datetime | None = None  # None-safe: set on create, always present after DB refresh

    # Nested readable names (populated via join)
    category_name: str | None = None
    account_name: str | None = None

    model_config = {"from_attributes": True}


class TransactionFilter(BaseModel):
    """Query parameters for filtering transactions."""
    start_date: datetime | None = None
    end_date: datetime | None = None
    category_id: UUID | None = None
    account_id: UUID | None = None
    type: TransactionType | None = None
    tag: str | None = None
    limit: int = Field(default=50, le=200)
    offset: int = Field(default=0, ge=0)


class MagicInputRequest(BaseModel):
    prompt: str = Field(
        min_length=5,
        max_length=500,
        examples=["Paid 450 for Netflix subscription using Credit Card"],
    )
