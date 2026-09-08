"""
app/models/transaction.py
──────────────────────────
SQLAlchemy ORM model for the `transactions` table.
"""

import enum
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4, UUID as PyUUID

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TransactionType(str, enum.Enum):
    EXPENSE  = "EXPENSE"
    INCOME   = "INCOME"
    TRANSFER = "TRANSFER"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),  # keep txn if account deleted
        nullable=True,
        index=True,
    )
    category_id: Mapped[PyUUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type_enum"),
        default=TransactionType.EXPENSE,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, nullable=False, server_default="{}"
    )
    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    user     = relationship("User",     back_populates="transactions")
    account  = relationship("Account",  back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.type} amount={self.amount}>"
