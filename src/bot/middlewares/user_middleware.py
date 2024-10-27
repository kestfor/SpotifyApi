from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, types
from aiogram.types import Update

from src.sql.engine import get_session
from src.sql.models.user import User


class UserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any],
    ) -> Any:
        from_user = None
        if isinstance(event, types.Message | types.CallbackQuery | types.InlineQuery):
            from_user = event.from_user
        if from_user:
            session = data.get("session")
            if session is None:
                async with get_session() as session:
                    user = await User.get_or_create(
                        session=session,
                        user_id=from_user.id,
                        username=from_user.username,
                    )
                    data["user"] = user
                    return await handler(event, data)
            else:
                user = await User.get_or_create(
                    session=session,
                    user_id=from_user.id,
                    username=from_user.username,
                )
                data["user"] = user
                return await handler(event, data)
        return await handler(event, data)
