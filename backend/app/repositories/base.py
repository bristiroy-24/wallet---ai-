"""
app/repositories/base.py
─────────────────────────
Generic async BaseRepository implementing standard CRUD operations.

Design: Repository Pattern
  – Isolates data access from business/service logic.
  – All DB queries live in repositories; services never call
    SQLAlchemy directly.
  – Uses Python generics so concrete repositories stay thin.
"""

from typing import Any, Generic, Sequence, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic repository providing async CRUD for any SQLAlchemy model.

    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, db: AsyncSession):
                super().__init__(User, db)
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get(self, id: UUID) -> ModelType | None:
        """Fetch a single record by primary key."""
        return await self.db.get(self.model, id)

    async def get_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[ModelType]:
        """Fetch all records with pagination."""
        result = await self.db.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def create(self, obj: ModelType) -> ModelType:
        """Persist a new model instance."""
        self.db.add(obj)
        await self.db.flush()   # assigns DB-generated values (id, defaults)
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType, data: dict[str, Any]) -> ModelType:
        """Patch an existing model instance with a dict of field→value."""
        for field, value in data.items():
            if hasattr(obj, field):
                setattr(obj, field, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        """Remove a model instance from the database."""
        await self.db.delete(obj)
        await self.db.flush()
