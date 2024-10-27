import asyncio

import aiogram

from src.bot.middlewares.database_session_middleware import DatabaseMiddleware
from src.bot.middlewares.session_member_middleware import SessionMemberMiddleware
from src.bot.middlewares.user_middleware import UserMiddleware
from src.config_reader import Settings
from aiogram import Bot, Dispatcher
from handlers import router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data_base import db
import logging

from src.sql.engine import async_session


# logging.basicConfig(level=logging.WARNING, filename='../bot_log.log', filemode='w')


async def main():
    settings = Settings()
    token = settings.bot_token.get_secret_value()
    bot = Bot(token=token)
    dp = Dispatcher()

    dp.message.middleware(DatabaseMiddleware(async_session))
    dp.callback_query.middleware(DatabaseMiddleware(async_session))

    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    dp.message.middleware(SessionMemberMiddleware())
    dp.callback_query.middleware(SessionMemberMiddleware())

    scheduler = AsyncIOScheduler()
    db.add_scheduler(scheduler)
    scheduler.start()
    dp.include_routers(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
