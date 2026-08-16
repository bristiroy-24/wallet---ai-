"""
app/routers/analytics.py
─────────────────────────
GET /api/v1/analytics/dashboard  – aggregated stats for the UI
GET /api/v1/analytics/insights   – AI-generated financial notifications
POST /api/v1/analytics/insights/refresh – trigger new AI insight generation
DELETE /api/v1/analytics/insights/{id}  – dismiss an insight
"""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_ai_service, get_current_user_id, get_db
from app.models.ai_insight import AIInsight
from app.repositories.insight import InsightRepository
from app.repositories.transaction import TransactionRepository
from app.schemas.ai import DashboardSchema, InsightRead
from app.services.ai_base import BaseAIService
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardSchema)
async def get_dashboard(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns:
      - Net balance and per-account breakdown
      - Category totals for the current month (Pie Chart data)
      - Last 6 months income/expense (Bar Chart data)
    """
    service = AnalyticsService(db)
    return await service.get_dashboard(user_id)


@router.get("/insights", response_model=list[InsightRead])
async def get_insights(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Return all non-dismissed AI insights for the current user."""
    repo = InsightRepository(db)
    return await repo.list_active(user_id)


@router.post(
    "/insights/refresh",
    response_model=list[InsightRead],
    status_code=status.HTTP_201_CREATED,
    summary="Regenerate AI insights",
)
async def refresh_insights(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ai_service: BaseAIService = Depends(get_ai_service),
):
    """
    Fetches last 30 days of transactions, calls the AI service to
    generate fresh insights, persists them, and returns the new list.
    """
    txn_repo     = TransactionRepository(db)
    insight_repo = InsightRepository(db)

    # Build human-readable transaction summaries for the AI prompt
    recent_txns = await txn_repo.get_last_30_days(user_id)
    summaries = [
        f"{t.type.value}: {t.note or (t.category.name if t.category else 'Unknown')} "
        f"– ₹{t.amount} on {t.date.strftime('%d %b')}"
        for t in recent_txns
    ]

    # Call AI service (Strategy Pattern in action)
    new_insights = await ai_service.generate_smart_insights(
        user_id=user_id,
        transaction_summaries=summaries,
    )

    # Persist the generated insights
    orm_insights = [
        AIInsight(
            id=uuid4(),
            user_id=user_id,
            insight_text=ins.insight_text,
            insight_type=ins.insight_type,
        )
        for ins in new_insights
    ]
    await insight_repo.bulk_create(orm_insights)
    await db.commit()

    return await insight_repo.list_active(user_id)


@router.delete(
    "/insights/{insight_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss an AI insight",
)
async def dismiss_insight(
    insight_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft-dismiss (hide) an AI insight notification."""
    repo = InsightRepository(db)
    await repo.dismiss(insight_id, user_id)
