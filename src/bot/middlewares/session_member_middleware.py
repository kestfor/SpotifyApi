from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Update

import src.bot.handlers as handlers


class SessionMemberMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any],
    ) -> Any:
        user = data['user']

        # TODO redirect to start
        if not user.in_session:
            await handlers.default_start(data['message'])
