"""
app/services/mock_ai_service.py
────────────────────────────────
MockAIService – drop-in replacement for GeminiAIService when no
API key is configured or during automated testing.

Implements the same BaseAIService interface, returns realistic
but hard-coded / keyword-derived responses instantly without
any network calls.
"""

import logging
import random
import re
from datetime import date
from uuid import UUID

from app.schemas.ai import InsightSchema, ParsedExpenseSchema
from app.models.ai_insight import InsightType
from app.services.ai_base import BaseAIService

logger = logging.getLogger(__name__)

# ── Keyword mappings mirroring the frontend mock parser ───────────────────────
_CATEGORY_KEYWORDS: list[tuple[str, str | None, list[str]]] = [
    ("Food & Drinks", "Zomato / Swiggy",  ["zomato", "swiggy", "food delivery"]),
    ("Food & Drinks", "Cafe / Coffee",    ["coffee", "starbucks", "cafe", "chai"]),
    ("Food & Drinks", "Restaurant",       ["lunch", "dinner", "breakfast", "restaurant", "pizza", "biryani", "meal"]),
    ("Entertainment", "Netflix",          ["netflix"]),
    ("Entertainment", "Amazon Prime",     ["amazon prime", "prime video"]),
    ("Entertainment", "Spotify",          ["spotify"]),
    ("Entertainment", None,               ["subscription", "hotstar", "disney", "gaming"]),
    ("Transport",     "Ola / Uber",       ["uber", "ola", "cab", "ride"]),
    ("Transport",     "Metro / Bus",      ["metro", "bus", "local"]),
    ("Transport",     "Fuel",             ["petrol", "diesel", "fuel"]),
    ("Housing",       "Groceries",        ["grocery", "groceries", "dmart", "bigbasket", "vegetables"]),
    ("Housing",       "Maid Salary",      ["maid", "bai", "cleaning"]),
    ("Housing",       "Electricity",      ["electricity", "power bill", "bescom"]),
    ("Housing",       None,               ["rent", "maintenance", "water bill"]),
    ("Recharge",      "Phone Recharge",   ["recharge", "airtel", "jio", "vi", "bsnl"]),
    ("Recharge",      "Wi-Fi Bill",       ["wifi", "wi-fi", "broadband", "internet bill"]),
    ("Shopping",      "Amazon / Flipkart",["amazon", "flipkart", "myntra", "meesho"]),
    ("Shopping",      None,               ["clothes", "shoes", "electronics", "gadget"]),
    ("Education",     None,               ["book", "course", "udemy", "school", "tuition"]),
    ("Health",        "Pharmacy",         ["medicine", "pharmacy", "chemist"]),
    ("Health",        "Doctor",           ["doctor", "clinic", "hospital"]),
]

_PAYMENT_KEYWORDS: dict[str, list[str]] = {
    "Card":         ["card", "credit", "debit", "swipe", "upi", "gpay", "phonepe", "paytm"],
    "Cash":         ["cash"],
    "Net Banking":  ["net banking", "neft", "rtgs", "imps", "bank transfer"],
}

_MOCK_INSIGHTS: list[tuple[str, InsightType]] = [
    ("⚠️ Your subscription spending is up 15% this week. Review active plans.", InsightType.WARNING),
    ("💡 You spend 40% of income on Food & Drinks. Meal prepping saves ~₹800/week.", InsightType.TIP),
    ("📊 Total spending this month is 12% lower than last month. Keep it up!", InsightType.SUCCESS),
    ("🔔 3 active subscriptions totalling ₹1,299/month detected.", InsightType.INFO),
    ("⚡ Transport costs spiked 30% this week. Check your cab usage.", InsightType.WARNING),
    ("✅ Great job! You stayed within your Food & Drinks budget this week.", InsightType.SUCCESS),
    ("💳 80% of expenses were digital payments. Cash usage is minimal.", InsightType.INFO),
    ("📉 Your savings rate dropped to 18% this month. Target is 30%.", InsightType.WARNING),
]


class MockAIService(BaseAIService):
    """
    Local, no-network mock of the AI service.

    Used when USE_REAL_AI=false (default) or in test suites.
    All responses are derived from keyword matching and/or
    random selection from realistic mock datasets.
    """

    async def parse_natural_language_expense(
        self,
        text: str,
        available_categories: list[str] | None = None,
    ) -> ParsedExpenseSchema:
        logger.debug(f"[MockAIService] parse_natural_language_expense: {text!r}")

        lower = text.lower()

        # Extract amount
        amount = 0.0
        match = re.search(r"[\₹rs]?\s*([\d,]+(?:\.\d{1,2})?)", text, re.IGNORECASE)
        if match:
            amount = float(match.group(1).replace(",", ""))

        # Detect type
        txn_type = "EXPENSE"
        if re.search(r"\b(salary|income|received|got paid|earned)\b", lower):
            txn_type = "INCOME"
        elif re.search(r"\b(transfer|sent to|moved)\b", lower):
            txn_type = "TRANSFER"

        # Detect payment method
        payment_method = "Cash"
        for method, keywords in _PAYMENT_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                payment_method = method
                break

        # Detect category + subcategory
        category, subcategory = "Other", None
        for cat, sub, keywords in _CATEGORY_KEYWORDS:
            if any(kw in lower for kw in keywords):
                category, subcategory = cat, sub
                break

        # Build clean note (strip the amount from the input)
        note = re.sub(r"[\₹rs]?\s*[\d,]+(?:\.\d{1,2})?\s*", "", text, flags=re.IGNORECASE).strip()
        note = note[:80] if note else text[:80]

        return ParsedExpenseSchema(
            amount=amount,
            type=txn_type,  # type: ignore[arg-type]
            category=category,
            subcategory=subcategory,
            payment_method=payment_method,
            note=note or text[:80],
            tags=[category.lower().split()[0]],
            date=None,
        )

    async def extract_receipt_data(
        self,
        image_bytes: bytes,
        mime_type: str,
        available_categories: list[str] | None = None,
    ) -> ParsedExpenseSchema:
        logger.debug(f"[MockAIService] extract_receipt_data: {len(image_bytes)} bytes, {mime_type}")

        # Return a realistic-looking mock receipt scan
        mock_amounts = [199.0, 349.5, 1249.0, 89.0, 450.0, 2100.0]
        mock_notes   = ["Grocery Store", "Restaurant Bill", "Electronics", "Pharmacy", "Supermarket"]

        return ParsedExpenseSchema(
            amount=random.choice(mock_amounts),
            type="EXPENSE",
            category="Shopping",
            subcategory=None,
            payment_method="Card",
            note=random.choice(mock_notes),
            tags=["receipt", "scanned"],
            date=date.today(),
        )

    async def generate_smart_insights(
        self,
        user_id: UUID,
        transaction_summaries: list[str],
    ) -> list[InsightSchema]:
        logger.debug(f"[MockAIService] generate_smart_insights for user {user_id}")

        # Return 3 randomly selected insights from the mock set
        selected = random.sample(_MOCK_INSIGHTS, min(3, len(_MOCK_INSIGHTS)))
        return [
            InsightSchema(insight_text=text, insight_type=itype)
            for text, itype in selected
        ]
