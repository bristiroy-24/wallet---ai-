"""
app/routers/analytics.py
─────────────────────────
Thin HTTP adapter for analytics and AI insight endpoints.

All business logic lives in:
  - AnalyticsService  → dashboard aggregation
  - InsightService    → insight generation, persistence, dismissal

Routers here only: parse request, call service, return response.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_ai_service, get_current_user_id, get_db
from app.schemas.ai import DashboardSchema, InsightRead
from app.services.ai_base import BaseAIService
from app.services.analytics_service import AnalyticsService
from app.services.insight_service import InsightService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardSchema)
async def get_dashboard(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns aggregated dashboard data:
      - Net balance and per-account balances
      - Category spending breakdown for the current month (Pie Chart)
      - Monthly income/expense trends for the last 6 months (Bar Chart)
    """
    service = AnalyticsService(db)
    return await service.get_dashboard(user_id)


@router.get("/insights", response_model=list[InsightRead])
async def get_insights(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ai_service: BaseAIService = Depends(get_ai_service),
):
    """Return all non-dismissed AI insights for the current user."""
    service = InsightService(db, ai_service)
    return await service.get_active(user_id)


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
    Triggers a full insight regeneration pipeline via InsightService:
    fetches recent transactions → calls AI → persists → returns new list.
    """
    service = InsightService(db, ai_service)
    return await service.regenerate(user_id)


@router.delete(
    "/insights/{insight_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dismiss an AI insight",
)
async def dismiss_insight(
    insight_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ai_service: BaseAIService = Depends(get_ai_service),
):
    """Soft-dismiss an AI insight notification."""
    service = InsightService(db, ai_service)
    await service.dismiss(insight_id, user_id)
