"""
app/repositories/transaction.py
─────────────────────────────────
Handles all transaction queries including rich filtering and
analytics aggregations.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Transaction, db)

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        category_id: UUID | None = None,
        account_id: UUID | None = None,
        txn_type: TransactionType | None = None,
        tag: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        """Filtered, paginated transaction list for a user."""
        filters = [Transaction.user_id == user_id]

        if start_date:
            filters.append(Transaction.date >= start_date)
        if end_date:
            filters.append(Transaction.date <= end_date)
        if category_id:
            filters.append(Transaction.category_id == category_id)
        if account_id:
            filters.append(Transaction.account_id == account_id)
        if txn_type:
            filters.append(Transaction.type == txn_type)
        if tag:
            # PostgreSQL array contains operator
            filters.append(Transaction.tags.any(tag))  # type: ignore[attr-defined]

        result = await self.db.execute(
            select(Transaction)
            .where(and_(*filters))
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.account),
            )
            .order_by(Transaction.date.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().unique().all())

    async def get_last_30_days(self, user_id: UUID) -> list[Transaction]:
        """Fetch all transactions in the past 30 days (for AI insights)."""
        since = datetime.now(timezone.utc) - timedelta(days=30)
        result = await self.db.execute(
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.date >= since,
            )
            .options(joinedload(Transaction.category))
            .order_by(Transaction.date.desc())
        )
        return list(result.scalars().unique().all())

    async def category_totals_this_month(
        self, user_id: UUID
    ) -> list[tuple[str, str | None, Decimal]]:
        """
        Returns tuples of (category_name, category_color, total_spend)
        for EXPENSE transactions in the current calendar month.

        Tuple field order matches CategoryBreakdown schema construction:
          index 0 → category_name  (str)
          index 1 → color          (str | None)
          index 2 → total          (Decimal)

        Used for the Pie Chart on the dashboard.
        """
        now = datetime.now(timezone.utc)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        result = await self.db.execute(
            select(
                Category.name,
                Category.color,
                func.sum(Transaction.amount).label("total"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.date >= start,
            )
            .group_by(Category.name, Category.color)
            .order_by(func.sum(Transaction.amount).desc())
        )
        return result.all()  # type: ignore[return-value]

    async def monthly_totals(
        self, user_id: UUID, months: int = 6
    ) -> list[tuple[int, int, Decimal, Decimal]]:
        """
        Returns (year, month, total_expense, total_income) for the
        last N months. Used for the Bar Chart.
        """
        since = datetime.now(timezone.utc).replace(day=1) - timedelta(days=months * 30)

        result = await self.db.execute(
            select(
                func.extract("year",  Transaction.date).label("year"),
                func.extract("month", Transaction.date).label("month"),
                func.sum(
                    case((Transaction.type == TransactionType.EXPENSE,  Transaction.amount), else_=0)
                ).label("expense"),
                func.sum(
                    case((Transaction.type == TransactionType.INCOME, Transaction.amount), else_=0)
                ).label("income"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.date >= since,
            )
            .group_by("year", "month")
            .order_by("year", "month")
        )
        return result.all()  # type: ignore[return-value]

    async def all_time_totals(
        self, user_id: UUID
    ) -> tuple[Decimal, Decimal]:
        """
        Returns (total_income, total_expense) for all time via SQL SUM+CASE.
        Never loads ORM objects into Python — O(1) regardless of history size.
        """
        result = await self.db.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.type == TransactionType.INCOME, Transaction.amount),
                            else_=0,
                        )
                    ),
                    Decimal("0"),
                ).label("income"),
                func.coalesce(
                    func.sum(
                        case(
                            (Transaction.type == TransactionType.EXPENSE, Transaction.amount),
                            else_=0,
                        )
                    ),
                    Decimal("0"),
                ).label("expense"),
            ).where(Transaction.user_id == user_id)
        )
        row = result.one()
        return Decimal(str(row.income)), Decimal(str(row.expense))
