"""
app/models/account.py
──────────────────────
SQLAlchemy ORM model for the `accounts` table.
Represents a user's financial account (cash wallet, debit/credit card, bank account).
"""

import enum
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AccountType(str, enum.Enum):
    CASH = "CASH"
    CARD = "CARD"
    BANK = "BANK"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, name="accounttype"), nullable=False, default=AccountType.BANK
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=15, scale=2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    color: Mapped[str | None] = mapped_column(String(9), nullable=True)  # hex color

    # Relationships
    user: Mapped["User"] = relationship(back_populates="accounts")  # noqa: F821
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Account id={self.id} name={self.name!r} type={self.type}>"
