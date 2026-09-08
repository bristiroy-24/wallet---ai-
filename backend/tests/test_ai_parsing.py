"""
tests/test_ai_parsing.py
─────────────────────────
Unit tests for MockAIService — natural language parsing, receipt OCR,
and smart insight generation.

These tests run entirely in-process with no DB or network calls.
They validate the Strategy interface contract so GeminiAIService can
be swapped in with confidence.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.schemas.ai import InsightSchema, ParsedExpenseSchema
from app.services.mock_ai_service import MockAIService


@pytest.fixture
def ai() -> MockAIService:
    return MockAIService()


# ── parse_natural_language_expense ────────────────────────────────────────────

class TestNaturalLanguageParsing:

    async def test_returns_parsed_expense_schema(self, ai):
        result = await ai.parse_natural_language_expense("Paid 450 for lunch")
        assert isinstance(result, ParsedExpenseSchema)

    async def test_amount_extracted_correctly(self, ai):
        result = await ai.parse_natural_language_expense("Spent 1200 on groceries")
        assert result.amount == pytest.approx(1200.0)

    async def test_amount_with_rupee_symbol(self, ai):
        result = await ai.parse_natural_language_expense("Paid ₹350 for zomato order")
        assert result.amount == pytest.approx(350.0)

    async def test_amount_with_comma(self, ai):
        result = await ai.parse_natural_language_expense("Paid 1,500 for rent")
        assert result.amount == pytest.approx(1500.0)

    async def test_food_category_detected(self, ai):
        result = await ai.parse_natural_language_expense("Had lunch at a restaurant")
        assert result.category == "Food & Drinks"

    async def test_zomato_subcategory_detected(self, ai):
        result = await ai.parse_natural_language_expense("Ordered from zomato")
        assert result.subcategory == "Zomato / Swiggy"

    async def test_netflix_category_detected(self, ai):
        result = await ai.parse_natural_language_expense("Paid for netflix subscription")
        assert result.category == "Entertainment"
        assert result.subcategory == "Netflix"

    async def test_transport_uber_detected(self, ai):
        result = await ai.parse_natural_language_expense("Took uber to airport")
        assert result.category == "Transport"
        assert result.subcategory == "Ola / Uber"

    async def test_income_type_detected(self, ai):
        result = await ai.parse_natural_language_expense("Received salary this month")
        assert result.type == "INCOME"

    async def test_transfer_type_detected(self, ai):
        result = await ai.parse_natural_language_expense("Transfer sent to HDFC account")
        assert result.type == "TRANSFER"

    async def test_card_payment_detected(self, ai):
        result = await ai.parse_natural_language_expense("Paid 500 via UPI")
        assert result.payment_method == "Card"

    async def test_cash_payment_is_default(self, ai):
        result = await ai.parse_natural_language_expense("Bought vegetables for 200")
        assert result.payment_method == "Cash"

    async def test_default_type_is_expense(self, ai):
        result = await ai.parse_natural_language_expense("Bought coffee for 100")
        assert result.type == "EXPENSE"

    async def test_unknown_expense_falls_back_to_other(self, ai):
        result = await ai.parse_natural_language_expense("Random thing 999")
        assert result.category == "Other"

    async def test_tags_list_returned(self, ai):
        result = await ai.parse_natural_language_expense("Netflix 649 subscription")
        assert isinstance(result.tags, list)
        assert len(result.tags) >= 1

    async def test_available_categories_accepted(self, ai):
        """Service should accept the optional categories list without crashing."""
        result = await ai.parse_natural_language_expense(
            "Dinner at restaurant",
            available_categories=["Food & Drinks", "Transport", "Other"],
        )
        assert isinstance(result, ParsedExpenseSchema)

    async def test_schema_fields_all_present(self, ai):
        result = await ai.parse_natural_language_expense("Paid 200 for medicine")
        # All required schema fields must exist
        assert hasattr(result, "amount")
        assert hasattr(result, "type")
        assert hasattr(result, "category")
        assert hasattr(result, "payment_method")
        assert hasattr(result, "tags")
        assert hasattr(result, "note")


# ── extract_receipt_data ──────────────────────────────────────────────────────

class TestReceiptOCR:

    async def test_returns_parsed_expense_schema(self, ai):
        result = await ai.extract_receipt_data(b"fake-image-bytes", "image/jpeg")
        assert isinstance(result, ParsedExpenseSchema)

    async def test_amount_is_positive(self, ai):
        result = await ai.extract_receipt_data(b"fake-image-bytes", "image/png")
        assert result.amount > 0

    async def test_type_is_expense(self, ai):
        result = await ai.extract_receipt_data(b"fake-image-bytes", "image/jpeg")
        assert result.type == "EXPENSE"

    async def test_date_is_set(self, ai):
        from datetime import date
        result = await ai.extract_receipt_data(b"fake-image-bytes", "image/jpeg")
        assert result.date == date.today()

    async def test_tags_contain_receipt(self, ai):
        result = await ai.extract_receipt_data(b"fake-image-bytes", "image/jpeg")
        assert "receipt" in result.tags

    async def test_accepts_webp_mime_type(self, ai):
        result = await ai.extract_receipt_data(b"fake-image-bytes", "image/webp")
        assert isinstance(result, ParsedExpenseSchema)


# ── generate_smart_insights ───────────────────────────────────────────────────

class TestInsightGeneration:

    async def test_returns_list_of_insights(self, ai):
        summaries = ["EXPENSE: Lunch – ₹350 on 01 Aug", "EXPENSE: Netflix – ₹649 on 03 Aug"]
        result = await ai.generate_smart_insights(uuid4(), summaries)
        assert isinstance(result, list)

    async def test_returns_insight_schema_instances(self, ai):
        result = await ai.generate_smart_insights(uuid4(), ["EXPENSE: Coffee – ₹100"])
        for item in result:
            assert isinstance(item, InsightSchema)

    async def test_insights_have_text_and_type(self, ai):
        result = await ai.generate_smart_insights(uuid4(), ["EXPENSE: Uber – ₹200"])
        for item in result:
            assert item.insight_text
            assert item.insight_type is not None

    async def test_returns_at_most_3_insights(self, ai):
        result = await ai.generate_smart_insights(uuid4(), ["tx1", "tx2"])
        assert len(result) <= 3

    async def test_empty_summaries_returns_list(self, ai):
        """Should return a list (possibly empty) without crashing."""
        result = await ai.generate_smart_insights(uuid4(), [])
        assert isinstance(result, list)


# ── Contract / interface compliance ──────────────────────────────────────────

class TestBaseAIServiceContract:
    """
    Verify MockAIService fully implements the BaseAIService ABC.
    This ensures GeminiAIService must implement the same interface.
    """

    def test_mock_is_instantiable(self):
        svc = MockAIService()
        assert svc is not None

    def test_mock_has_parse_method(self):
        assert callable(getattr(MockAIService, "parse_natural_language_expense", None))

    def test_mock_has_extract_method(self):
        assert callable(getattr(MockAIService, "extract_receipt_data", None))

    def test_mock_has_insights_method(self):
        assert callable(getattr(MockAIService, "generate_smart_insights", None))
