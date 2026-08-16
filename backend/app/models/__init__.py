"""
app/models/__init__.py
Central index for all database models.
"""

from app.models.account import Account
from app.models.ai_insight import AIInsight, InsightType
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.models.user import User

__all__ = [
    "User",
    "Account",
    "Category",
    "Transaction",
    "TransactionType",
    "AIInsight",
    "InsightType",
]