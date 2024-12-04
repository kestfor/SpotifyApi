from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Update

from src.bot.handlers.connect_user_to_session_route.connection_route import router as connection_router
from src.bot.handlers.init_handlers.init_handlers import router as init_router


class SessionMemberMiddleware(BaseMiddleware):
    __ALLOWED_ROUTES = [connection_router, init_router]

    @classmethod
    def _is_allowed_route(cls, data: Dict[str, Any]) -> bool:
        event_router = data['event_router']
        if event_router in cls.__ALLOWED_ROUTES:
            return True

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any],
    ) -> Any:
        user = data.get("user")
        if user.in_session or self._is_allowed_route(data):
            return await handler(event, data)
