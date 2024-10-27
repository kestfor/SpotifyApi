from sqlalchemy import select, delete
from sqlalchemy.dialects.mysql import insert

from src.session.user import TelegramUser
from src.sql.engine import async_session
from src.sql.tables import Session as SQL_SESSION
from src.sql.tables import User as SQL_USER
from src.sql.tables import UserInSession as SQL_USER_IN_SESSION


class SQLSessionController:

    def __init__(self, id: int, token: str) -> None:
        self._id = id
        self._token = token

    @classmethod
    async def get_session_by_user(cls, user: TelegramUser):
        async with async_session() as session, session.begin():
            session_id = await session.get(SQL_USER_IN_SESSION, user.user_id)
            return SQLSessionController(session_id, str(user.user_id))

    async def create(self) -> None:
        async with async_session() as session, session.begin():
            insert_stmt = insert(SQL_SESSION).values(id=self._id, token=self._token)
            on_dupl_stmt = insert_stmt.on_duplicate_key_update(insert_stmt.inserted)
            await session.execute(on_dupl_stmt)

    async def remove(self) -> None:
        async with async_session() as session, session.begin():
            await session.delete(SQL_USER_IN_SESSION).where(SQL_SESSION.id == self._id)
            await session.delete(SQL_SESSION).where(SQL_SESSION.id == self._id)

    async def get_users(self) -> list[int]:
        async with async_session() as session, session.begin():
            stmt = select(SQL_USER_IN_SESSION).where(SQL_USER_IN_SESSION.session_id == self._id)
            objects = (await session.execute(stmt)).scalars().all()
            return [item.user_id for item in objects]

    async def get_token(self) -> str | None:
        async with async_session() as session, session.begin():
            stmt = select(SQL_SESSION).where(SQL_SESSION.id == self._id)
            res = (await session.execute(stmt)).scalars().first()
            if res is not None:
                return res.token
            else:
                return None

    async def add_user(self, user: TelegramUser) -> None:
        async with async_session() as session, session.begin():
            await session.execute(insert(SQL_USER_IN_SESSION).values(session_id=self._id, user_id=user.user_id))

    async def remove_user(self, user_id: int) -> None:
        async with async_session() as session, session.begin():
            delete(SQL_USER_IN_SESSION).where(SQL_USER_IN_SESSION.user_id == user_id)


class SQLUser:

    def __init__(self, user_id, username):
        self._user = TelegramUser(user_id, username)

    async def auth_storage_id(self) -> int | None:
        async with async_session() as session, session.begin():
            auth_id = await session.get(SQL_USER, self._user.user_id)
            return auth_id
