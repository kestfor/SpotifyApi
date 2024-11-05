import asyncio

from aiogram import Bot

from src.env import BOT_TOKEN
from src.refresh_service.refresh_functions import update_all_sessions
from src.sql.engine import async_session

REFRESH_TIMEOUT = 30


async def main():
    token = BOT_TOKEN
    bot = Bot(token=token)
    while True:
        async with async_session() as session, session.begin():
            await update_all_sessions(session, bot)
            await asyncio.sleep(REFRESH_TIMEOUT)


if __name__ == "__main__":
    asyncio.run(main())
