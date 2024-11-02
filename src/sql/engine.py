from contextlib import asynccontextmanager

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.env import DB_HOST, DB_PORT, DB_PASSWORD, DB_USERNAME

DATABASE = {
    'drivername': 'mysql+asyncmy',
    'host': DB_HOST,
    'port': DB_PORT,
    'username': DB_USERNAME,
    'password': DB_PASSWORD,
    'database': 'share_music'
}

engine = create_async_engine(URL.create(**DATABASE))
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
