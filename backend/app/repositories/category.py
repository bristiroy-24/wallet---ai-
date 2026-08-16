"""app/repositories/category.py"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Category, db)

    async def get_root_categories(self) -> list[Category]:
        """
        Returns all top-level categories with their subcategories
        eagerly loaded in a single query.
        """
        result = await self.db.execute(
            select(Category)
            .where(Category.parent_id.is_(None))
            .options(selectinload(Category.subcategories))
            .order_by(Category.name)
        )
        return list(result.scalars().all())

    async def get_all_flat(self) -> list[Category]:
        """All categories (flat list, no eager loading)."""
        result = await self.db.execute(
            select(Category).order_by(Category.name)
        )
        return list(result.scalars().all())
