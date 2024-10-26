from sqlalchemy import URL
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.config_reader import config

DATABASE = {
    'drivername': 'mysql+asyncmy',
    'host': config.db_host.get_secret_value(),
    'port': config.db_port.get_secret_value(),
    'username': config.db_username.get_secret_value(),
    'password': config.db_password.get_secret_value(),
    'database': 'share_music'
}

engine = create_async_engine(URL.create(**DATABASE), isolation_level="SERIALIZABLE")
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
