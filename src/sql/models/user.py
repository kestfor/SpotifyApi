import logging
from typing import Union, Optional

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import mapped_column, relationship, Mapped

from src.sql.models.auth import Auth
from src.sql.models.base import Base
from src.sql.models.session import Session


class User(Base):
    __tablename__ = 'user'

    user_id = mapped_column(BigInteger, primary_key=True)
    username = mapped_column(String(255))
    auth_id = mapped_column(ForeignKey('auth.id'), nullable=True)
    session_id = mapped_column(ForeignKey("session.id"), nullable=True)

    auth: Mapped[Auth] = relationship(back_populates="user", lazy='joined')
    session: Mapped[Session] = relationship(back_populates="user", lazy='joined')

    @classmethod
    async def get_or_create(cls, session: AsyncSession, user_id: int, username: str = None):
        obj = await session.get(cls, user_id)
        if not obj:
            obj = cls(user_id=user_id, username=username)
            session.add(obj)
            await session.flush()
        return obj

    async def add_auth(self, session: AsyncSession, auth_id: int):
        auth = await session.get(Auth, auth_id)
        if auth is not None:
            self.auth = auth
        else:
            logging.warning(f"User {self.user_id} has no auth {auth_id}")

    async def add_to_session(self, session: AsyncSession, session_id: int):
        session = await session.get(Session, session_id)
        if session is not None:
            self.session = session
        else:
            logging.warning(f"User {self.user_id} has no session {session_id}")

    @property
    def authorized(self) -> bool:
        return self.auth is not None

    @property
    def in_session(self) -> bool:
        return self.session is not None

    @property
    def is_admin(self) -> bool:
        return self.session_id == self.user_id

    async def get_admin(self, session: AsyncSession) -> Optional['User']:
        if self.is_admin:
            return self
        elif not self.in_session:
            return None
        else:
            return await session.get(User, self.session_id)
