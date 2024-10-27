from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import mapped_column, Mapped, relationship, MappedColumn

from src.sql.models.base import Base

if TYPE_CHECKING:
    from src.sql.models.user import User


class Session(Base):
    __tablename__ = 'session'

    id: MappedColumn[int] = mapped_column(BigInteger, primary_key=True)
    token = mapped_column(String(255))

    user: Mapped['User'] = relationship(back_populates="session", lazy='selectin')

    async def users_num(self, session: AsyncSession) -> int:
        stmt = select(func.count()).select_from(self.__class__).where(self.id == self.__class__.id)
        return (await session.execute(stmt)).scalar()
