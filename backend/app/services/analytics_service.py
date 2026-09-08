"""
app/services/analytics_service.py
───────────────────────────────────
Computes dashboard analytics by aggregating data via repositories.

Design notes:
  - All DB aggregation is pushed down to SQL (never Python-side summation
    over large result sets).
  - Field names match DashboardSchema, CategoryBreakdown, MonthlyTrend,
    and AccountSummary exactly — schemas/ai.py is the canonical contract.
  - Routers instantiate this service; no repo calls happen in routers.
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.account import AccountRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.ai import (
    AccountSummary,
    CategoryBreakdown,
    DashboardSchema,
    MonthlyTrend,
)


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self._txn_repo     = TransactionRepository(db)
        self._account_repo = AccountRepository(db)

    async def get_dashboard(self, user_id: UUID) -> DashboardSchema:
        """
        Returns all data needed by the frontend dashboard in one call:
          - Account list with balances
          - This-month category breakdown (Pie Chart)
          - Last-6-month income/expense trends (Bar Chart)
          - Net balance, total income, total expense (all-time, via SQL)
        """
        accounts     = await self._account_repo.list_by_user(user_id)
        cat_totals   = await self._txn_repo.category_totals_this_month(user_id)
        monthly_data = await self._txn_repo.monthly_totals(user_id, months=6)

        # ── Net balance: sum of account balances (no transaction scan) ────────
        net_balance = sum((a.balance for a in accounts), Decimal("0"))

        # ── All-time income/expense via SQL aggregation (not Python sum) ──────
        # monthly_totals covers all history when months is large enough;
        # for all-time we use a dedicated repo method.
        income_total, expense_total = await self._txn_repo.all_time_totals(user_id)

        # ── Category breakdown (Pie Chart) ────────────────────────────────────
        category_breakdown = [
            CategoryBreakdown(
                category_name=name,
                total=Decimal(str(total or 0)),
                color=color,
            )
            for name, color, total in cat_totals
        ]

        # ── Monthly trends (Bar Chart) ────────────────────────────────────────
        _MONTHS = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        monthly_trends = [
            MonthlyTrend(
                month=f"{_MONTHS[int(month) - 1]} {int(year)}",
                total_expense=Decimal(str(expense or 0)),
                total_income=Decimal(str(income or 0)),
            )
            for year, month, expense, income in monthly_data
        ]

        # ── Accounts list ─────────────────────────────────────────────────────
        account_summaries = [
            AccountSummary(
                id=str(a.id),
                name=a.name,
                type=a.type.value,
                balance=a.balance,
                currency=a.currency,
                color=a.color,
            )
            for a in accounts
        ]

        return DashboardSchema(
            net_balance=net_balance,
            total_income=income_total,
            total_expense=expense_total,
            accounts=account_summaries,
            category_breakdown=category_breakdown,
            monthly_trends=monthly_trends,
        )
