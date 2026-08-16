"""
app/services/ai_factory.py
───────────────────────────
AIFactory – Factory Pattern implementation.

Decides at runtime which AI service implementation to return based
on application settings. Callers only know about BaseAIService.

Design: Factory Pattern + Strategy Pattern combined
  – Factory creates the right Strategy.
  – The FastAPI dependency `get_ai_service()` calls this factory,
    keeping router code completely decoupled from the decision.
"""

import logging

from app.core.config import Settings
from app.services.ai_base import BaseAIService

logger = logging.getLogger(__name__)


class AIFactory:
    """
    Static factory for creating the appropriate AI service.

    Usage:
        service: BaseAIService = AIFactory.create(settings)
    """

    # Cache the instance to avoid re-initialising the Gemini client per request
    _instance: BaseAIService | None = None
    _use_real_ai: bool | None = None

    @classmethod
    def create(cls, settings: Settings) -> BaseAIService:
        """
        Returns a cached BaseAIService implementation.

        If USE_REAL_AI=true (and GEMINI_API_KEY is set) → GeminiAIService
        Otherwise → MockAIService
        """
        # Re-create if settings changed (e.g. test overrides)
        if cls._instance is None or cls._use_real_ai != settings.USE_REAL_AI:
            cls._use_real_ai = settings.USE_REAL_AI

            if settings.USE_REAL_AI and settings.GEMINI_API_KEY:
                from app.services.gemini_service import GeminiAIService
                cls._instance = GeminiAIService()
                logger.info("[AIFactory] Using GeminiAIService (production mode)")
            else:
                from app.services.mock_ai_service import MockAIService
                cls._instance = MockAIService()
                logger.info(
                    "[AIFactory] Using MockAIService "
                    f"(USE_REAL_AI={settings.USE_REAL_AI}, "
                    f"key_set={bool(settings.GEMINI_API_KEY)})"
                )

        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Force re-creation on next call. Used in tests."""
        cls._instance = None
        cls._use_real_ai = None
