"""
app/models/ai_insight.py
──────────────────────────
SQLAlchemy ORM model for the `ai_insights` table.

InsightType is defined in app/schemas/ai.py and imported here
so the enum has one canonical home in the schema layer, not the
persistence layer. Services can import it from schemas without
touching ORM internals.
"""

from datetime import datetime, timezone
from uuid import uuid4, UUID as PyUUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.schemas.ai import InsightType  # single source of truth


class AIInsight(Base):
    __tablename__ = "ai_insights"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insight_text: Mapped[str] = mapped_column(Text, nullable=False)
    insight_type: Mapped[InsightType] = mapped_column(
        Enum(InsightType, name="insight_type_enum"),
        default=InsightType.INFO,
        nullable=False,
    )
    is_dismissed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Relationship
    user = relationship("User", back_populates="insights")

    def __repr__(self) -> str:
        return f"<AIInsight id={self.id} type={self.insight_type} dismissed={self.is_dismissed}>"
