"""
app/services/analytics_service.py
───────────────────────────────────
Computes dashboard analytics by aggregating data from multiple
repositories. Keeps all business logic out of the routers.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.account import AccountRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.ai import CategoryBreakdown, DashboardSchema, MonthlyTrend


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self._txn_repo     = TransactionRepository(db)
        self._account_repo = AccountRepository(db)

    async def get_dashboard(self, user_id: UUID) -> DashboardSchema:
        accounts      = await self._account_repo.list_by_user(user_id)
        cat_totals    = await self._txn_repo.category_totals_this_month(user_id)
        monthly_data  = await self._txn_repo.monthly_totals(user_id, months=6)

        # Net balance = sum of all account balances
        net_balance = float(sum(a.balance for a in accounts))

        # Aggregate income / expense from all-time transactions
        all_txns = await self._txn_repo.list_by_user(user_id, limit=1000)
        total_income  = sum(float(t.amount) for t in all_txns if t.type.value == "INCOME")
        total_expense = sum(float(t.amount) for t in all_txns if t.type.value == "EXPENSE")

        # Category breakdown for Pie Chart
        category_breakdown = [
            CategoryBreakdown(
                category_name=name,
                total=float(total),
                color=color,
            )
            for name, color, total in cat_totals
        ]

        # Monthly trends for Bar Chart
        _MONTHS = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
        monthly_trends = [
            MonthlyTrend(
                month=f"{_MONTHS[int(month) - 1]} {int(year)}",
                total_expense=float(expense or Decimal("0")),
                total_income=float(income or Decimal("0")),
            )
            for year, month, expense, income in monthly_data
        ]

        return DashboardSchema(
            net_balance=net_balance,
            total_income=total_income,
            total_expense=total_expense,
            accounts=[
                {
                    "id":       str(a.id),
                    "name":     a.name,
                    "type":     a.type.value,
                    "balance":  float(a.balance),
                    "currency": a.currency,
                    "color":    a.color,
                }
                for a in accounts
            ],
            category_breakdown=category_breakdown,
            monthly_trends=monthly_trends,
        )
