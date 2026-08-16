"""app/repositories/account.py"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Account, db)

    async def list_by_user(self, user_id: UUID) -> list[Account]:
        result = await self.db.execute(
            select(Account)
            .where(Account.user_id == user_id)
            .order_by(Account.name)
        )
        return list(result.scalars().all())

    async def get_user_account(self, account_id: UUID, user_id: UUID) -> Account | None:
        result = await self.db.execute(
            select(Account).where(
                Account.id == account_id,
                Account.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
