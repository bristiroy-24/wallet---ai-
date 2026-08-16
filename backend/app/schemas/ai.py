"""
app/schemas/ai.py
Pydantic schemas for AI-driven response parsing, insights, and dashboard analytics.
"""

from datetime import date as datetime_date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.ai_insight import InsightType


class InsightSchema(BaseModel):
    id: Optional[UUID] = None
    insight_text: str
    insight_type: InsightType = InsightType.INFO
    is_dismissed: bool = False


class InsightRead(InsightSchema):
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ParsedExpenseSchema(BaseModel):
    amount: Optional[Decimal] = Field(
        default=None, 
        description="Extracted numeric transaction amount"
    )
    category: Optional[str] = Field(
        default=None, 
        description="Primary category (e.g. Food & Drinks, Housing)"
    )
    subcategory: Optional[str] = Field(
        default=None, 
        description="Nested subcategory if applicable"
    )
    payment_method: Optional[str] = Field(
        default=None, 
        description="Payment account/method used (e.g. Cash, Card, Bank)"
    )
    date: Optional[datetime_date] = Field(
        default=None, 
        description="Transaction date in YYYY-MM-DD format"
    )
    tags: List[str] = Field(
        default_factory=list, 
        description="Extracted tags or keywords"
    )
    note: Optional[str] = Field(
        default=None, 
        description="Brief description or merchant name"
    )


class CategoryBreakdown(BaseModel):
    category_name: str
    total_amount: Decimal = Decimal("0.00")
    percentage: float = 0.0


class MonthlyTrend(BaseModel):
    month: str
    income: Decimal = Decimal("0.00")
    expense: Decimal = Decimal("0.00")


class DashboardSchema(BaseModel):
    total_balance: Decimal = Decimal("0.00")
    accounts_summary: List[Dict[str, Any]] = Field(default_factory=list)
    category_pie_data: List[CategoryBreakdown] = Field(default_factory=list)
    monthly_trend_bar_data: List[MonthlyTrend] = Field(default_factory=list)
    insights: List[InsightRead] = Field(default_factory=list)

    class Config:
        from_attributes = True