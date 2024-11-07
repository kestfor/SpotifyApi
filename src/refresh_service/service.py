import asyncio
import logging

from aiogram import Bot

from src.env import BOT_TOKEN
from src.refresh_service.refresh_functions import update_all_sessions
from src.sql.engine import async_session, get_session

REFRESH_TIMEOUT = 5


async def main():
    token = BOT_TOKEN
    while True:
        try:
            bot = Bot(token=token)
            async with get_session() as session:
                await update_all_sessions(session, bot)
                await bot.session.close()
                await asyncio.sleep(REFRESH_TIMEOUT)
        except Exception as e:
            logging.error(e)
            await asyncio.sleep(REFRESH_TIMEOUT)


if __name__ == "__main__":
    asyncio.run(main())
