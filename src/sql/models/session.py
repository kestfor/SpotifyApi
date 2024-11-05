from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import mapped_column, Mapped, relationship

import src.sql.models.user as user_model
from src.sql.models.base import Base

if TYPE_CHECKING:
    from src.sql.models.user import User


class Session(Base):
    __tablename__ = 'session'

    id = mapped_column(BigInteger, primary_key=True)
    token = mapped_column(String(255))

    user: Mapped[list['User']] = relationship(back_populates="session", lazy='selectin')

    @classmethod
    async def get_by_id(cls, session: AsyncSession, session_id: int) -> Optional['Session']:
        return await session.get(cls, session_id)

    @classmethod
    async def get_all(cls, sql_session: AsyncSession) -> list['Session']:
        stmt = select(cls)
        return list(await sql_session.scalars(stmt))

    async def users_num(self, session: AsyncSession) -> int:
        stmt = select(user_model.User).where(user_model.User.session_id == self.id)
        return len(list((await session.scalars(stmt))))

    async def get_users(self, session: AsyncSession) -> list['User']:
        stmt = select(user_model.User).where(user_model.User.session_id == self.id)
        return list(await session.scalars(stmt))

    async def delete(self, session: AsyncSession) -> None:
        await session.delete(self)
        await session.flush()
