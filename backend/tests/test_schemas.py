"""
tests/test_schemas.py
──────────────────────
Unit tests for Pydantic schema validation.

Covers:
  - ParsedExpenseSchema field types and defaults
  - TransactionCreate validation rules
  - DashboardSchema construction
  - InsightSchema / InsightRead
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.transaction import TransactionType
from app.schemas.ai import (
    CategoryBreakdown,
    DashboardSchema,
    InsightRead,
    InsightSchema,
    InsightType,
    MonthlyTrend,
    ParsedExpenseSchema,
)
from app.schemas.transaction import TransactionCreate, TransactionRead


# ── ParsedExpenseSchema ───────────────────────────────────────────────────────

class TestParsedExpenseSchema:

    def test_defaults_are_safe(self):
        s = ParsedExpenseSchema()
        assert s.type == "EXPENSE"
        assert s.tags == []
        assert s.amount is None
        assert s.category is None

    def test_all_fields_accepted(self):
        s = ParsedExpenseSchema(
            amount=Decimal("450"),
            type="INCOME",
            category="Food & Drinks",
            subcategory="Restaurant",
            payment_method="Card",
            date=date.today(),
            tags=["food", "lunch"],
            note="Dinner at a nice place",
        )
        assert s.amount == Decimal("450")
        assert s.type == "INCOME"
        assert len(s.tags) == 2

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            ParsedExpenseSchema(type="INVALID_TYPE")

    def test_tags_default_to_empty_list(self):
        s = ParsedExpenseSchema(amount=Decimal("100"), category="Other")
        assert s.tags == []


# ── TransactionCreate ─────────────────────────────────────────────────────────

class TestTransactionCreate:

    def test_valid_minimal_create(self):
        t = TransactionCreate(amount=Decimal("100"))
        assert t.amount == Decimal("100")
        assert t.type == TransactionType.EXPENSE

    def test_amount_must_be_positive(self):
        with pytest.raises(ValidationError):
            TransactionCreate(amount=Decimal("0"))

    def test_negative_amount_raises(self):
        with pytest.raises(ValidationError):
            TransactionCreate(amount=Decimal("-50"))

    def test_tags_default_to_empty(self):
        t = TransactionCreate(amount=Decimal("200"))
        assert t.tags == []

    def test_all_transaction_types_accepted(self):
        for txn_type in TransactionType:
            t = TransactionCreate(amount=Decimal("100"), type=txn_type)
            assert t.type == txn_type

    def test_note_max_length_enforced(self):
        with pytest.raises(ValidationError):
            TransactionCreate(amount=Decimal("100"), note="x" * 1001)


# ── TransactionRead ───────────────────────────────────────────────────────────

class TestTransactionRead:

    def test_from_dict(self):
        now = datetime.now(timezone.utc)
        r = TransactionRead(
            id=uuid4(),
            user_id=uuid4(),
            account_id=None,
            category_id=None,
            amount=Decimal("500"),
            type=TransactionType.EXPENSE,
            note="Test",
            tags=["test"],
            date=now,
            created_at=now,
        )
        assert r.amount == Decimal("500")

    def test_created_at_is_optional(self):
        """created_at=None should not raise a ValidationError."""
        now = datetime.now(timezone.utc)
        r = TransactionRead(
            id=uuid4(), user_id=uuid4(), account_id=None, category_id=None,
            amount=Decimal("100"), type=TransactionType.INCOME,
            note=None, tags=[], date=now, created_at=None,
        )
        assert r.created_at is None

    def test_category_and_account_names_optional(self):
        now = datetime.now(timezone.utc)
        r = TransactionRead(
            id=uuid4(), user_id=uuid4(), account_id=None, category_id=None,
            amount=Decimal("100"), type=TransactionType.EXPENSE,
            note=None, tags=[], date=now,
        )
        assert r.category_name is None
        assert r.account_name is None


# ── DashboardSchema ───────────────────────────────────────────────────────────

class TestDashboardSchema:

    def test_empty_dashboard_has_defaults(self):
        d = DashboardSchema()
        assert d.net_balance == Decimal("0.00")
        assert d.accounts == []
        assert d.category_breakdown == []
        assert d.monthly_trends == []

    def test_category_breakdown_construction(self):
        cb = CategoryBreakdown(
            category_name="Food & Drinks",
            total=Decimal("5000"),
            color="#EF4444",
        )
        assert cb.category_name == "Food & Drinks"
        assert cb.total == Decimal("5000")
        assert cb.color == "#EF4444"

    def test_monthly_trend_construction(self):
        mt = MonthlyTrend(
            month="Aug 2026",
            total_expense=Decimal("20000"),
            total_income=Decimal("65000"),
        )
        assert mt.month == "Aug 2026"
        assert mt.total_expense == Decimal("20000")


# ── InsightSchema / InsightRead ───────────────────────────────────────────────

class TestInsightSchemas:

    def test_insight_schema_defaults(self):
        s = InsightSchema(insight_text="⚠️ Warning: high spend")
        assert s.insight_type == InsightType.INFO

    def test_insight_type_values(self):
        for itype in InsightType:
            s = InsightSchema(insight_text="test", insight_type=itype)
            assert s.insight_type == itype

    def test_insight_read_from_attributes(self):
        r = InsightRead(
            id=uuid4(),
            insight_text="💡 Save more",
            insight_type=InsightType.TIP,
            is_dismissed=False,
        )
        assert r.insight_text == "💡 Save more"
        assert r.is_dismissed is False
