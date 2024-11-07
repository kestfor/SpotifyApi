import asyncio
import logging
import sys

from aiogram import Bot

from src.env import BOT_TOKEN
from src.refresh_service.refresh_functions import update_all_sessions
from src.sql.engine import async_session, get_session

REFRESH_TIMEOUT = 30

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s - %(levelname)s - %(filename)s %(funcName)s: %(lineno)d - %(message)s",
                    handlers=[
                        # logging.FileHandler("../../log.log", encoding="utf-8"),
                        logging.StreamHandler(sys.stdout)
                    ])

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
