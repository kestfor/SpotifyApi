from sqlalchemy import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

DATABASE = {
    'drivername': 'mysql+asyncmy',
    'host': '46.226.167.110',
    'port': '3306',
    'username': 'test',
    'password': "654321",
    'database': 'share_music'
}

engine = create_async_engine(URL.create(**DATABASE), isolation_level="SERIALIZABLE")
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
