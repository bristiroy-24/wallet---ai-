"""
app/routers/categories.py
──────────────────────────
GET /api/v1/categories – returns the full category tree
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.repositories.category import CategoryRepository
from app.schemas.category import CategoryRead

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=list[CategoryRead])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """
    Returns all top-level categories with their subcategories nested.
    No auth required – categories are shared across all users.
    """
    repo = CategoryRepository(db)
    return await repo.get_root_categories()
