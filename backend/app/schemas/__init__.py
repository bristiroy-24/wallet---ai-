"""app/schemas – public package API."""
from app.schemas.ai import (
    InsightType,
    ParsedExpenseSchema,
    InsightSchema,
    InsightRead,
    CategoryBreakdown,
    MonthlyTrend,
    AccountSummary,
    DashboardSchema,
)
from app.schemas.user import UserCreate, UserRead, TokenResponse, LoginRequest
from app.schemas.account import AccountCreate, AccountRead, AccountUpdate
from app.schemas.category import CategoryRead
from app.schemas.transaction import TransactionCreate, TransactionRead, TransactionFilter, MagicInputRequest

__all__ = [
    # AI / Analytics
    "InsightType", "ParsedExpenseSchema", "InsightSchema", "InsightRead",
    "CategoryBreakdown", "MonthlyTrend", "AccountSummary", "DashboardSchema",
    # User
    "UserCreate", "UserRead", "TokenResponse", "LoginRequest",
    # Account
    "AccountCreate", "AccountRead", "AccountUpdate",
    # Category
    "CategoryRead",
    # Transaction
    "TransactionCreate", "TransactionRead", "TransactionFilter", "MagicInputRequest",
]
