"""
app/main.py
────────────
FastAPI application factory.

Responsibilities:
  1. Create and configure the FastAPI app instance.
  2. Register CORS middleware for frontend integration.
  3. Mount all API routers under /api/v1.
  4. Register a global exception handler that converts domain
     errors (AppError subclasses) into clean HTTP responses.
  5. Run database table creation + category seeding on startup.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import AsyncSessionLocal, create_all_tables

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on application startup:
      1. Creates all DB tables (dev only – use Alembic in prod).
      2. Seeds default categories if the table is empty.
    """
    logger.info(f"Starting {settings.PROJECT_NAME} [{settings.APP_ENV}]")

    # Table creation (idempotent – safe to run every startup)
    await create_all_tables()
    logger.info("Database tables verified.")

    # Seed default categories
    from app.db.seed import seed_categories
    async with AsyncSessionLocal() as db:
        await seed_categories(db)
    logger.info("Category seed complete.")

    yield  # ← app is running

    logger.info(f"{settings.PROJECT_NAME} shutting down.")


# ── Application factory ───────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=(
            "Production-ready Expense Tracker REST API. "
            "Powered by FastAPI, PostgreSQL, and Google Gemini AI."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows local frontend (Live Server, file://, localhost)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global exception handler ──────────────────────────────────────────────
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """
        Converts any AppError (or subclass) raised anywhere in the stack
        into a standardised JSON error response.
        """
        logger.warning(f"AppError on {request.url}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled exception on {request.url}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected server error occurred."},
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    from app.routers import accounts, analytics, auth, categories, transactions

    prefix = settings.API_V1_PREFIX  # /api/v1

    app.include_router(auth.router,         prefix=prefix)
    app.include_router(accounts.router,     prefix=prefix)
    app.include_router(categories.router,   prefix=prefix)
    app.include_router(transactions.router, prefix=prefix)
    app.include_router(analytics.router,    prefix=prefix)

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health():
        return {"status": "ok", "env": settings.APP_ENV}

    # ── Serve frontend static files ───────────────────────────────────────────
    # Mounts the project root (parent of backend/) so index.html, app.js,
    # style.css, api.js are all served at http://localhost:8000/
    frontend_dir = Path(__file__).resolve().parent.parent.parent  # ExpenseTrackerApp/
    if frontend_dir.exists() and (frontend_dir / "index.html").exists():
        # Serve index.html at root
        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(str(frontend_dir / "index.html"))

        # Mount all other static files (app.js, style.css, api.js, etc.)
        app.mount("/", StaticFiles(directory=str(frontend_dir)), name="frontend")
        logger.info(f"Frontend served from: {frontend_dir}")
    else:
        logger.warning(f"Frontend directory not found at: {frontend_dir}")

    logger.info(f"Registered routes under {prefix}")
    return app


# ── WSGI / ASGI entry point ───────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )