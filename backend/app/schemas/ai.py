"""
app/schemas/ai.py
──────────────────
Pydantic DTOs for all AI-related API boundaries.

These schemas serve THREE purposes:
  1. API response models     — what routers return to the client
  2. Gemini response_schema  — passed to Gemini structured-output calls
  3. Service layer contracts — what AI services return to callers

All field names here are the canonical source of truth.
analytics_service.py, gemini_service.py, and mock_ai_service.py
must all use these exact field names.
"""

from datetime import date as DateType, datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Moved here from app/models/ai_insight.py so the service layer ─────────────
# ── does not need to import from the ORM/persistence layer. ───────────────────
import enum


class InsightType(str, enum.Enum):
    WARNING = "WARNING"
    TIP     = "TIP"
    INFO    = "INFO"
    SUCCESS = "SUCCESS"


# ── AI Parsing ────────────────────────────────────────────────────────────────

class ParsedExpenseSchema(BaseModel):
    """
    Structured output schema sent to Gemini as response_schema.
    Also returned by /transactions/magic-input and /transactions/scan-receipt.
    """
    amount: Optional[Decimal] = Field(
        default=None,
        description="Extracted numeric transaction amount, e.g. 450.00",
    )
    type: Literal["EXPENSE", "INCOME", "TRANSFER"] = Field(
        default="EXPENSE",
        description="Transaction type",
    )
    category: Optional[str] = Field(
        default=None,
        description="Best-matching category name, e.g. 'Food & Drinks'",
    )
    subcategory: Optional[str] = Field(
        default=None,
        description="Nested subcategory name, or null if not applicable",
    )
    payment_method: Optional[str] = Field(
        default=None,
        description="Payment method: Cash, Card, UPI, etc.",
    )
    date: Optional[DateType] = Field(
        default=None,
        description="Transaction date YYYY-MM-DD, or null if not mentioned",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Up to 3 relevant lowercase tags",
    )
    note: Optional[str] = Field(
        default=None,
        description="Short description or merchant name (max 80 chars)",
    )


# ── Insights ──────────────────────────────────────────────────────────────────

class InsightSchema(BaseModel):
    """Used by AI services as a return type and by Gemini as response_schema."""
    insight_text: str = Field(
        description="Concise actionable insight, starts with emoji, max 140 chars"
    )
    insight_type: InsightType = Field(default=InsightType.INFO)


class InsightRead(BaseModel):
    """Returned by the /analytics/insights API endpoint."""
    id: UUID
    insight_text: str
    insight_type: InsightType
    is_dismissed: bool

    model_config = {"from_attributes": True}


# ── Dashboard / Analytics ─────────────────────────────────────────────────────

class CategoryBreakdown(BaseModel):
    """One slice of the Pie Chart — spending by category for the current month."""
    category_name: str = Field(
        description="Category name, e.g. 'Food & Drinks'"
    )
    total: Decimal = Field(
        default=Decimal("0.00"),
        description="Total amount spent in this category this month",
    )
    color: Optional[str] = Field(
        default=None,
        description="Hex colour string from the category row, e.g. '#EF4444'",
    )


class MonthlyTrend(BaseModel):
    """One bar of the Bar Chart — income vs expense per month."""
    month: str                              # e.g. "Jul 2026"
    total_expense: Decimal = Decimal("0.00")
    total_income:  Decimal = Decimal("0.00")


class AccountSummary(BaseModel):
    """Account entry inside DashboardSchema."""
    id: str
    name: str
    type: str
    balance: Decimal
    currency: str
    color: Optional[str] = None


class DashboardSchema(BaseModel):
    """Full dashboard response returned by GET /analytics/dashboard."""
    net_balance:        Decimal = Decimal("0.00")
    total_income:       Decimal = Decimal("0.00")
    total_expense:      Decimal = Decimal("0.00")
    accounts:           List[AccountSummary]      = Field(default_factory=list)
    category_breakdown: List[CategoryBreakdown]   = Field(default_factory=list)
    monthly_trends:     List[MonthlyTrend]        = Field(default_factory=list)
