"""app/repositories/insight.py"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_insight import AIInsight
from app.repositories.base import BaseRepository


class InsightRepository(BaseRepository[AIInsight]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(AIInsight, db)

    async def list_active(self, user_id: UUID) -> list[AIInsight]:
        """Returns all non-dismissed insights for a user, newest first."""
        result = await self.db.execute(
            select(AIInsight)
            .where(AIInsight.user_id == user_id, AIInsight.is_dismissed.is_(False))
            .order_by(AIInsight.created_at.desc())
        )
        return list(result.scalars().all())

    async def dismiss(self, insight_id: UUID, user_id: UUID) -> None:
        """Soft-dismiss an insight."""
        await self.db.execute(
            update(AIInsight)
            .where(AIInsight.id == insight_id, AIInsight.user_id == user_id)
            .values(is_dismissed=True)
        )

    async def bulk_create(self, insights: list[AIInsight]) -> None:
        """Persist a batch of new insight rows."""
        for insight in insights:
            self.db.add(insight)
        await self.db.flush()
