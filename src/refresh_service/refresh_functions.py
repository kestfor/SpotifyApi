import asyncio
import random

import aiogram
from aiogram.exceptions import TelegramBadRequest
from asyncspotify import FullTrack
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.spotify_sessions import spotify_sessions
from src.bot.utils.keyboards import get_admin_menu_keyboard, get_user_menu_keyboard
from src.bot.utils.utils import get_volume_emoji
from src.spotify.spotify import AsyncSpotify
from src.sql.models.meta import ScreenName
from src.sql.models.session import Session
from src.sql.models.user import User


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
        print(f"screen for user {user} updated")
    except TelegramBadRequest as error:
        print(error)


async def update_session(music_session: Session, sql_session: AsyncSession, bot: aiogram.Bot):
    users = await music_session.get_users(sql_session)
    master = await users[0].get_master(sql_session)
    spotify: AsyncSpotify = await spotify_sessions.get_or_create(master, sql_session)
    try:
        await spotify.update()
    except Exception:
        return
    curr_track = await spotify.get_curr_track()
    volume = spotify.volume
    is_playing = spotify.is_playing
    num_of_users = len(users)

    tasks = []
    for user in users:
        tasks.append(asyncio.create_task(refresh(curr_track, volume, is_playing, num_of_users, user, bot)))
    await asyncio.gather(*tasks)


async def update_all_sessions(sql_session: AsyncSession, bot: aiogram.Bot):
    sessions = await Session.get_all(sql_session)
    tasks = []
    for session in sessions:
        tasks.append(asyncio.create_task(update_session(session, sql_session, bot)))
    await asyncio.gather(*tasks)
