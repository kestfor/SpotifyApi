import logging
from typing import Callable, Dict, Any, Awaitable
from uuid import uuid4

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

logger = logging.getLogger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, session: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]) -> Any:
        async with self.session_maker() as session:
            async with session.begin():
                data['session'] = session
                return await handler(event, data)
