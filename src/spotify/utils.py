import functools

import asyncspotify

from src.spotify.spotify_errors import PremiumRequired, UnsupportedDevice


def error_wrapper():
    def wrapper(function):
        @functools.wraps(function)
        async def wrapped(*args, **kwargs):
            try:
                res = await function(*args, **kwargs)
            except asyncspotify.Forbidden:
                raise PremiumRequired
            except UnsupportedDevice as e:
                raise e
            except Exception:
                raise ConnectionError
            return res

        return wrapped

    return wrapper
