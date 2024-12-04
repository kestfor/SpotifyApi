import os

import redis.asyncio as redis


def get_database_cfg(n, **kwargs):
    config = {
        'host': os.getenv("DB_HOST"),
        'username': os.getenv("REDIS_USER"),
        'port': '6379',
        'password': os.getenv("REDIS_PASSWORD"),
        'db': n,
        'decode_responses': True,
        'socket_connect_timeout': 60,
        'socket_timeout': 5,
    }
    config.update(kwargs)
    return config


redis_states_storage = redis.Redis(**get_database_cfg(0))
