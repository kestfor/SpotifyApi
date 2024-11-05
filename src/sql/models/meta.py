from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, BigInteger
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import mapped_column, relationship, Mapped

from src.sql.models.base import Base

if TYPE_CHECKING:
    from src.sql.models.user import User


class ScreenName:
    MAIN = "MAIN"
    EMPTY = "EMPTY"


screen_names = (ScreenName.MAIN, ScreenName.EMPTY)
screen_name = ENUM(*screen_names, name="screen")


class Meta(Base):
    __tablename__ = 'meta'

    user_id = mapped_column(ForeignKey('user.user_id'), primary_key=True)
    last_message_id = mapped_column(BigInteger)
    screen = mapped_column(screen_name, nullable=False)

    user: Mapped['User'] = relationship(back_populates='meta', lazy='selectin')

    @classmethod
    async def get_or_create(cls, session: AsyncSession, user_id: int) -> 'Meta':
        obj = await session.get(cls, user_id)
        if not obj:
            obj = cls(user_id=user_id)
            session.add(obj)
            await session.flush()
        return obj

