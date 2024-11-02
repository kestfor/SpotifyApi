from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware, types, Bot
from aiogram.types import Update

from src.sql.models.user import User


class UserMiddleware(BaseMiddleware):

    @staticmethod
    async def _delete_prev_message(user: User, data: Dict[str, Any]):
        bot: Bot = data.get("bot")
        if user.last_message_id is not None:
            try:
                await bot.delete_message(user.user_id, user.last_message_id)
            except:
                pass

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any],
    ) -> Any:
        from_user = None
        if isinstance(event, types.Message | types.CallbackQuery | types.InlineQuery | types.BotCommand):
            from_user = event.from_user
        if from_user:
            session = data.get("session")

            user = await User.get_or_create(
                session=session,
                user_id=from_user.id,
                username=from_user.username,
            )

            match event:
                case types.Message():
                    await self._delete_prev_message(user, data)
                    user.last_message_id = event.message_id
                case types.CallbackQuery():
                    user.last_message_id = event.message.message_id

            data["user"] = user

            return await handler(event, data)
