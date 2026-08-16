"""
app/services/gemini_service.py
───────────────────────────────
Production AI service using the official google-genai SDK.

Key design decisions:
  1. Uses genai.Client() (the newer unified client, not the legacy
     google.generativeai module).
  2. Structured outputs: passes ParsedExpenseSchema / InsightSchema
     as response_schema to Gemini, guaranteeing valid JSON that maps
     directly to Pydantic models – no fragile string parsing.
  3. Multimodal receipt OCR: uses types.Part.from_bytes() to send
     raw image bytes alongside the text prompt.
  4. All external calls are wrapped in try/except and raise the
     domain-level AIServiceError so the router layer is clean.
"""

import json
import logging
from uuid import UUID

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import AIServiceError
from app.schemas.ai import InsightSchema, ParsedExpenseSchema
from app.services.ai_base import BaseAIService


# Module-level wrapper so Gemini receives a proper list schema
class _InsightListWrapper(BaseModel):
    insights: list[InsightSchema]

logger = logging.getLogger(__name__)


# ── System prompts ─────────────────────────────────────────────────────────────

_PARSE_SYSTEM_PROMPT = """You are a financial assistant for an expense tracker app.
Extract structured expense information from the user's natural language input.

Rules:
- Map to the closest category from the provided list.
- If no category matches, use "Other".
- Only include date if explicitly mentioned; otherwise set to null.
- Tags should be lowercase, relevant keywords (max 3).
- Note should be a clean, brief description (max 80 chars).
- Amount must be a positive number. If unclear, set to 0.
"""

_RECEIPT_SYSTEM_PROMPT = """You are an OCR assistant for an expense tracker app.
Carefully read the receipt image and extract:
  - Total amount paid (numeric, no currency symbols)
  - Merchant / shop name (use as note)
  - Date of transaction (YYYY-MM-DD) if visible
  - Best-fitting category from the provided list

Return only the JSON fields requested. Do not add commentary.
"""

_INSIGHTS_SYSTEM_PROMPT = """You are a proactive financial advisor analysing a user's
recent transactions. Generate 3 to 5 concise, actionable insights.

Each insight must:
  - Start with a relevant emoji.
  - Be under 140 characters.
  - Be categorised as one of: WARNING, TIP, INFO, SUCCESS.
  - Be specific to the data (avoid generic advice).

Examples:
  ⚠️ Your Entertainment spend is up 40% vs last month – 3 subscriptions active.
  💡 You spent ₹3,200 on food delivery this month. Cooking saves ~₹800/week.
  ✅ Great job! Your total spending this month is 12% lower than last month.
"""


class GeminiAIService(BaseAIService):
    """
    Production AI service backed by Google Gemini.

    Instantiated once by AIFactory and shared across requests
    (stateless – safe to reuse).
    """

    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise AIServiceError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file or set USE_REAL_AI=false to use MockAIService."
            )
        # Initialise the unified Gemini client
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = settings.GEMINI_MODEL
        logger.info(f"[GeminiAIService] Initialised with model: {self._model}")

    # ── 1. Natural Language Parser ────────────────────────────────────────────

    async def parse_natural_language_expense(
        self,
        text: str,
        available_categories: list[str] | None = None,
    ) -> ParsedExpenseSchema:
        """
        Sends the user's free-text input to Gemini with a structured
        output schema. Gemini returns JSON that maps 1:1 to ParsedExpenseSchema.
        """
        category_hint = (
            f"\nAvailable categories: {', '.join(available_categories)}"
            if available_categories
            else ""
        )
        prompt = f"{_PARSE_SYSTEM_PROMPT}{category_hint}\n\nUser input: {text}"

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ParsedExpenseSchema,  # structured output
                    temperature=0.2,  # low temp for deterministic parsing
                ),
            )
            # With structured output, response.text is already valid JSON
            data = json.loads(response.text)
            return ParsedExpenseSchema.model_validate(data)

        except Exception as exc:
            logger.error(f"[GeminiAIService] parse_natural_language_expense failed: {exc}")
            raise AIServiceError(f"Gemini NLP parsing failed: {exc}") from exc

    # ── 2. Receipt OCR ────────────────────────────────────────────────────────

    async def extract_receipt_data(
        self,
        image_bytes: bytes,
        mime_type: str,
        available_categories: list[str] | None = None,
    ) -> ParsedExpenseSchema:
        """
        Sends the receipt image to Gemini as a multimodal input.
        Gemini performs OCR and returns structured expense data.
        """
        category_hint = (
            f"\nAvailable categories: {', '.join(available_categories)}"
            if available_categories
            else ""
        )
        text_prompt = f"{_RECEIPT_SYSTEM_PROMPT}{category_hint}"

        # Build multimodal content: image part + text instruction
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=[image_part, text_prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ParsedExpenseSchema,
                    temperature=0.1,  # near-deterministic for OCR
                ),
            )
            data = json.loads(response.text)
            return ParsedExpenseSchema.model_validate(data)

        except Exception as exc:
            logger.error(f"[GeminiAIService] extract_receipt_data failed: {exc}")
            raise AIServiceError(f"Gemini OCR failed: {exc}") from exc

    # ── 3. Smart Insights ─────────────────────────────────────────────────────

    async def generate_smart_insights(
        self,
        user_id: UUID,
        transaction_summaries: list[str],
    ) -> list[InsightSchema]:
        """
        Feeds 30-day transaction history to Gemini and gets back
        a structured list of financial insights.
        """
        if not transaction_summaries:
            return []

        txn_block = "\n".join(
            f"- {summary}" for summary in transaction_summaries[:40]
        )
        prompt = (
            f"{_INSIGHTS_SYSTEM_PROMPT}\n\n"
            f"User's transactions (last 30 days):\n{txn_block}"
        )

        # Schema for an array of InsightSchema — defined at module level above

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_InsightListWrapper,
                    temperature=0.7,
                ),
            )
            data = json.loads(response.text)
            wrapper = _InsightListWrapper.model_validate(data)
            logger.info(
                f"[GeminiAIService] Generated {len(wrapper.insights)} insights "
                f"for user {user_id}"
            )
            return wrapper.insights

        except Exception as exc:
            logger.error(f"[GeminiAIService] generate_smart_insights failed: {exc}")
            raise AIServiceError(f"Gemini insights failed: {exc}") from exc
