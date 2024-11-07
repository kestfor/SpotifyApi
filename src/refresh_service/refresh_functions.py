import asyncio
import logging
import random
import time

import aiogram
from asyncspotify import FullTrack
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.spotify_sessions import spotify_sessions
from src.bot.utils.keyboards import get_admin_menu_keyboard, get_user_menu_keyboard
from src.bot.utils.utils import get_volume_emoji
from src.spotify.spotify import AsyncSpotify
from src.sql.models.meta import ScreenName
from src.sql.models.session import Session
from src.sql.models.user import User

USER_LIMIT = 25
TIME_OUT_SECONDS = 1


def get_part_of_users(users: list[User]):
    for index in range(0, len(users), USER_LIMIT):
        yield users[index: min(len(users), index + USER_LIMIT)]


def create_text(curr_track: FullTrack, volume, is_playing, num_of_users):
    emoji_artists = '🥺🤫😐🙄😮😄😆🥹🙂😌😙😎😏🤩😋🥶🥵🤭🤔😈'
    image_url = curr_track.album.images[0].url

    volume_str = f"{get_volume_emoji(volume)}: {volume}%\n\n" if is_playing else ""
    artists, name = [artist.name for artist in curr_track.artists], curr_track.name
    text = (
        f'<a href="{image_url}"> </a>\n'
        f'🎧: <b>{name}</b>\n\n'
        f'<i>{"".join(random.choices(emoji_artists, k=len(artists)))}️: {", ".join(artists)}</i>\n\n'
        f'{volume_str}'
        f'🔥 людей в сессии:'
        f' {num_of_users}')
    return text


async def refresh(curr_track, volume, is_playing, num_of_users, user: User, bot: aiogram.Bot):
    if user.last_message_id is None or user.meta.screen != ScreenName.MAIN:
        return
    text = create_text(curr_track, volume, is_playing, num_of_users)
    if user.is_master:
        keyboard = get_admin_menu_keyboard()
    else:
        keyboard = get_user_menu_keyboard()

    try:
        await bot.edit_message_text(message_id=user.last_message_id,
                                    chat_id=user.user_id,
                                    text=text, reply_markup=keyboard,
                                    parse_mode="HTML")
    except Exception as error:
        logging.error(error)


async def update_session(music_session: Session, sql_session: AsyncSession, bot: aiogram.Bot):
    start = time.time()
    users = await music_session.get_users(sql_session)
    master = await users[0].get_master(sql_session)
    spotify: AsyncSpotify = await spotify_sessions.get_or_create(master, sql_session)
    try:
        curr_track = await spotify.get_curr_track()
    except Exception as error:
        logging.error(error)
        return
    volume = spotify.volume
    is_playing = spotify.is_playing
    num_of_users = len(users)

    tasks = []
    for users_part in get_part_of_users(users):
        s = time.time()
        for user in users_part:
            tasks.append(asyncio.create_task(refresh(curr_track, volume, is_playing, num_of_users, user, bot)))
        await asyncio.gather(*tasks)
        time_left = time.time() - s
        if time_left < TIME_OUT_SECONDS:
            await asyncio.sleep(TIME_OUT_SECONDS - time_left)
    await spotify.close()
    print(f"session {music_session.id} updated in {time.time() - start} seconds")


async def update_all_sessions(sql_session: AsyncSession, bot: aiogram.Bot):
    sessions = await Session.get_all(sql_session)
    for session in sessions:
        await update_session(session, sql_session, bot)
