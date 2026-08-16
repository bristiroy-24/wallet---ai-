"""
app/services/ai_base.py
────────────────────────
Abstract base class (interface) for all AI service implementations.

Design: Strategy Pattern
  – Defines the contract that both GeminiAIService and MockAIService
    must fulfil.
  – Callers (routers / other services) program to BaseAIService,
    not to a concrete implementation.
  – Swapping AI providers requires zero changes outside this file
    and the factory.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.schemas.ai import InsightSchema, ParsedExpenseSchema


class BaseAIService(ABC):
    """
    Strategy interface for AI-powered expense features.

    All methods are async to allow non-blocking I/O with
    external AI API calls.
    """

    @abstractmethod
    async def parse_natural_language_expense(
        self,
        text: str,
        available_categories: list[str] | None = None,
    ) -> ParsedExpenseSchema:
        """
        Parse a free-text expense description into a structured
        ParsedExpenseSchema object.

        Args:
            text: Natural language input, e.g.
                  "Paid 450 for Netflix subscription using Credit Card"
            available_categories: Optional list of category names from
                  the user's database to help the AI pick the right one.

        Returns:
            ParsedExpenseSchema with amount, category, subcategory,
            payment_method, note, tags, and date.
        """
        ...

    @abstractmethod
    async def extract_receipt_data(
        self,
        image_bytes: bytes,
        mime_type: str,
        available_categories: list[str] | None = None,
    ) -> ParsedExpenseSchema:
        """
        Perform multimodal OCR on a receipt image and return
        structured transaction data.

        Args:
            image_bytes: Raw bytes of the uploaded image file.
            mime_type:   MIME type, e.g. "image/jpeg" or "image/png".
            available_categories: Optional category list for mapping.

        Returns:
            ParsedExpenseSchema with at minimum amount and note populated.
        """
        ...

    @abstractmethod
    async def generate_smart_insights(
        self,
        user_id: UUID,
        transaction_summaries: list[str],
    ) -> list[InsightSchema]:
        """
        Analyse a user's recent spending and generate proactive
        actionable financial insights.

        Args:
            user_id:               UUID of the user (for logging / tracing).
            transaction_summaries: List of human-readable transaction strings
                                   (last 30 days) already formatted by the
                                   calling service.

        Returns:
            List of InsightSchema objects (3–5 insights).
        """
        ...
