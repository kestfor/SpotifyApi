import asyncio
import datetime
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.bot.handlers.connect_user_to_session_route.connection_route import router as connect_users_router
from src.bot.handlers.init_handlers.init_handlers import router as init_router
from src.bot.handlers.invites.view_invites import router as invites_router
from src.bot.handlers.main_handlers.handlers import router as main_router
from src.bot.middlewares.database_session_middleware import DatabaseMiddleware
from src.bot.middlewares.session_member_middleware import SessionMemberMiddleware
from src.bot.middlewares.user_middleware import UserMiddleware
from src.bot.redis_conf import redis_states_storage
from src.env import BOT_TOKEN
from src.sql.engine import async_session

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(filename)s %(funcName)s: %(lineno)d - %(message)s",
                    handlers=[
                        # logging.FileHandler("../../log.log", encoding="utf-8"),
                        logging.StreamHandler(sys.stdout)
                    ])

storage = RedisStorage(redis_states_storage, key_builder=DefaultKeyBuilder(with_destiny=True),
                       data_ttl=datetime.timedelta(days=7), state_ttl=datetime.timedelta(days=7))


async def main():
    token = BOT_TOKEN
    bot = Bot(token=token)

    dp = Dispatcher(storage=storage)

    # dp.message.middleware(RetryMiddleware(delay=2))
    # dp.callback_query.middleware(RetryMiddleware(delay=2))

    dp.message.middleware(DatabaseMiddleware(async_session))
    dp.callback_query.middleware(DatabaseMiddleware(async_session))

    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())

    dp.message.middleware(SessionMemberMiddleware())
    dp.callback_query.middleware(SessionMemberMiddleware())

    scheduler = AsyncIOScheduler()
    scheduler.start()
    dp.include_routers(init_router, connect_users_router, main_router, invites_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
