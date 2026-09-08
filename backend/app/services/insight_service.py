"""
app/services/insight_service.py
────────────────────────────────
InsightService encapsulates all business logic for AI insight generation.

Design: Service layer pattern
  - Routers call InsightService; they never touch repositories directly
    for this flow.
  - InsightService orchestrates: fetch transactions → format summaries
    → call AI (Strategy) → persist insights → return results.
  - The router stays as a thin HTTP adapter (parse request, call service,
    return response).
"""

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_insight import AIInsight
from app.repositories.insight import InsightRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.ai import InsightRead, InsightSchema
from app.services.ai_base import BaseAIService


class InsightService:
    def __init__(self, db: AsyncSession, ai_service: BaseAIService) -> None:
        self._txn_repo     = TransactionRepository(db)
        self._insight_repo = InsightRepository(db)
        self._ai            = ai_service

    async def get_active(self, user_id: UUID) -> list[InsightRead]:
        """Return all non-dismissed insights for a user."""
        rows = await self._insight_repo.list_active(user_id)
        return [InsightRead.model_validate(r) for r in rows]

    async def regenerate(self, user_id: UUID) -> list[InsightRead]:
        """
        Full insight refresh pipeline:
          1. Fetch last 30 days of transactions from the DB.
          2. Format human-readable summaries for the AI prompt.
          3. Call the AI service (Strategy — Gemini or Mock).
          4. Persist new AIInsight ORM rows.
          5. Return the updated active insight list.
        """
        # Step 1 & 2 — fetch and format
        recent_txns = await self._txn_repo.get_last_30_days(user_id)
        summaries = [
            f"{t.type.value}: "
            f"{t.note or (t.category.name if t.category else 'Unknown')} "
            f"– ₹{t.amount} on {t.date.strftime('%d %b')}"
            for t in recent_txns
        ]

        # Step 3 — AI call (Strategy Pattern)
        generated: list[InsightSchema] = await self._ai.generate_smart_insights(
            user_id=user_id,
            transaction_summaries=summaries,
        )

        # Step 4 — persist
        orm_rows = [
            AIInsight(
                id=uuid4(),
                user_id=user_id,
                insight_text=ins.insight_text,
                insight_type=ins.insight_type,
            )
            for ins in generated
        ]
        await self._insight_repo.bulk_create(orm_rows)

        # Step 5 — return refreshed list
        return await self.get_active(user_id)

    async def dismiss(self, insight_id: UUID, user_id: UUID) -> None:
        """Soft-dismiss an insight so it no longer appears."""
        await self._insight_repo.dismiss(insight_id, user_id)
