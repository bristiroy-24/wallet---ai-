"""
app/core/config.py
──────────────────
Centralised application settings loaded from environment variables
or a .env file via pydantic-settings.

All sensitive values (API keys, DB URLs, secrets) are read here and
never hard-coded anywhere else in the codebase.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.

    Priority order (highest → lowest):
      1. Actual environment variables
      2. .env file in the project root
      3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    PROJECT_NAME: str = Field(default="WalletAI API")
    API_V1_PREFIX: str = Field(default="/api/v1")

    # ── Database ───────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/walletai",
        description="Async SQLAlchemy PostgreSQL connection string",
    )

    # ── Authentication ─────────────────────────────────────
    SECRET_KEY: str = Field(default="CHANGE_ME_INSECURE_DEFAULT_KEY")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10080)  # 7 days

    # ── Google Gemini AI ───────────────────────────────────
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API key. Get yours at makersuite.google.com",
    )
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash")
    USE_REAL_AI: bool = Field(
        default=False,
        description="Set to true to use real Gemini API; false uses MockAIService",
    )

    # ── CORS ───────────────────────────────────────────────
    # Keep as plain string; parsed into a list by the property below
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://127.0.0.1:5500",
        description="Comma-separated list of allowed CORS origins",
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        """Returns ALLOWED_ORIGINS as a Python list."""
        v = self.ALLOWED_ORIGINS.strip()
        if v.startswith("["):
            import json as _json
            try:
                return _json.loads(v)
            except Exception:
                pass
        return [o.strip() for o in v.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns a cached Settings singleton.
    Use FastAPI's Depends(get_settings) to inject into endpoints.
    """
    return Settings()


# Module-level convenience instance
settings = get_settings()
