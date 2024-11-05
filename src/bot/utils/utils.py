import asyncio
import functools
import random
from string import ascii_letters, digits

import aiogram
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.callbacks_factory.factories import GetNextLyrics
from src.spotify.spotify import AsyncSpotify
from src.spotify.track_in_queue import TrackWithUser
from src.sql.models.session import Session
from src.sql.models.user import User


def generate_token(length) -> str:
    token = ''.join([random.choice(ascii_letters + digits) for _ in range(length)])
    return token


def get_volume_emoji(volume: int):
    volumes = "🔇🔈🔉🔊"
    if volume == 0:
        return volumes[0]
    elif 0 < volume <= 33:
        return volumes[1]
    elif 33 < volume <= 66:
        return volumes[2]
    elif 66 < volume <= 100:
        return volumes[3]


async def get_menu_text(spotify: AsyncSpotify, user: User, sql_session: AsyncSession):
    emoji_artists = '🥺🤫😐🙄😮😄😆🥹🙂😌😙😎😏🤩😋🥶🥵🤭🤔😈'
    curr_track = await spotify.get_curr_track()
    image_url = curr_track.album.images[0].url

    num_of_users = await user.users_in_session_num(sql_session)

    volume = spotify.volume
    volume_str = f"{get_volume_emoji(volume)}: {volume}%\n\n" if spotify.is_playing else ""
    artists, name = [artist.name for artist in curr_track.artists], curr_track.name
    text = (
        f'<a href="{image_url}"> </a>\n'
        f'🎧: <b>{name}</b>\n\n'
        f'<i>{"".join(random.choices(emoji_artists, k=len(artists)))}️: {", ".join(artists)}</i>\n\n'
        f'{volume_str}'
        f'🔥 людей в сессии:'
        f' {num_of_users}')
    return text


async def get_queue_text(spotify: AsyncSpotify):
    queue: list[TrackWithUser] = await spotify.get_curr_user_queue()
    max_items_num = 10
    if len(queue) == 0:
        return None
    else:
        queue = queue[0:max_items_num]
        text = ""
        for item in queue:
            author = ' - поставил(а) @' + item.username
            text += (item.track.name[
                     :item.track.name.find('(')] if '(' in item.track.name else item.track.name) + author + '\n\n'
        return text


def get_lyrics_switcher(start, end, step):
    builder = InlineKeyboardBuilder()
    if start != 0:
        builder.row(InlineKeyboardButton(text='◀️', callback_data=GetNextLyrics(start_ind=start - step, step=16,
                                                                                action='decrement').pack()))
    if end != -1:
        builder.add(InlineKeyboardButton(text='▶️', callback_data=GetNextLyrics(start_ind=start + step, step=16,
                                                                                action='increment').pack()))
    builder.row(InlineKeyboardButton(text='меню', callback_data="menu"))
    return builder.as_markup()


async def get_curr_song_info(lyrics):
    artist, name = lyrics.artist, lyrics.name
    name = name[:name.find('(')] if '(' in name else name
    name = name.strip()
    return '🔥 ' + artist + ' ' + name + ' 🔥\n\n'


def save_users_last_message_id():
    """
    if wrapped function returns aiogram Message object, it saves its id to user object
    """

    def wrapper(function):
        @functools.wraps(function)
        async def wrapped(*args, **kwargs):
            user = kwargs.get("user")

            res = await function(*args, **kwargs)
            if isinstance(res, types.Message):
                user.last_message_id = res.message_id

        return wrapped

    return wrapper


async def notify_of_session_end(user: User, bot: aiogram.Bot):
    try:
        await bot.delete_message(user.user_id, user.last_message_id)
        user.last_message_id = None
    except TelegramBadRequest:
        pass
    finally:
        pass
        # msg = await bot.send_message(user.user_id, "сессия завершена")
        # user.last_message_id = msg.message_id
        # await asyncio.sleep(3)
