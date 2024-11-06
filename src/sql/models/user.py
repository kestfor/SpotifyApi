import logging
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String, select
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import mapped_column, relationship, Mapped

from src.sql.models.auth import Auth
from src.sql.models.base import Base
from src.sql.models.meta import Meta
from src.sql.models.session import Session


class ROLES:
    MASTER = "MASTER"
    ADMIN = "ADMIN"
    NORMAL = "NORMAL"


roles = (ROLES.MASTER, ROLES.ADMIN, ROLES.NORMAL)
role_enum = ENUM(*roles, name="role")


class User(Base):
    __tablename__ = 'user'

    __repr_attrs__ = ["user_id", "username", "auth_id", "session_id"]

    user_id = mapped_column(BigInteger, primary_key=True)
    username = mapped_column(String(255))
    # user_role = mapped_column(role_enum, nullable=True)
    auth_id = mapped_column(ForeignKey('auth.id'), nullable=True)
    session_id = mapped_column(ForeignKey("session.id", ondelete="SET NULL"), nullable=True)

    auth: Mapped[Auth] = relationship(back_populates="user", lazy='joined')
    session: Mapped[Session] = relationship(back_populates="user", lazy='joined')
    meta: Mapped[Meta] = relationship(back_populates="user", lazy='joined')

    @classmethod
    async def get_or_create(cls, session: AsyncSession, user_id: int, username: str = None):
        obj = await session.get(cls, user_id)
        if not obj:
            obj = cls(user_id=user_id, username=username)
            session.add(obj)
            meta = await Meta.get_or_create(session, user_id)
            obj.meta = meta
            await session.flush()
        return obj

    async def add_auth(self, session: AsyncSession, hash: str):
        auth = (await session.execute(select(Auth).where(Auth.hash == hash))).scalar()
        if auth is not None:
            self.auth = auth
            self.auth_id = auth.id
        else:
            logging.warning(f"User {self.user_id} has no auth with hash {hash}")

    async def add_to_session(self, session: AsyncSession, music_session: Session):
        if music_session is not None:
            self.session = music_session
            self.session_id = music_session.id
            # self.user_role = ROLES.NORMAL
            await session.flush()
        else:
            logging.warning(f"User {self.user_id} has no session music session")

    async def users_in_session_num(self, session: AsyncSession) -> int:
        if self.session_id is None:
            return 0
        stmt = select(User).where(User.session_id == self.session_id)
        return len(list((await session.scalars(stmt))))

    async def leave_session(self, session: AsyncSession):
        self.session_id = None
        # self.user_role = None
        await session.flush()

    async def create_session(self, session: AsyncSession, token: str) -> Session:
        music_session = await session.get(Session, token)
        if music_session is None:
            music_session = Session(id=self.user_id, token=token)
            session.add(music_session)
            # self.user_role = ROLES.MASTER
            await session.flush()
        self.session = music_session
        return self.session

    @property
    def last_message_id(self) -> int:
        return self.meta.last_message_id

    @last_message_id.setter
    def last_message_id(self, last_message_id: int):
        self.meta.last_message_id = last_message_id

    @property
    def authorized(self) -> bool:
        return self.auth is not None

    @property
    def in_session(self) -> bool:
        return self.session is not None

    @property
    def is_master(self) -> bool:
        return self.session_id == self.user_id

    @property
    def token(self) -> str:
        return str(self.user_id)

    async def get_master(self, session: AsyncSession) -> Optional['User']:
        if self.is_master:
            return self
        elif not self.in_session:
            return None
        else:
            return await session.get(User, self.session_id)
