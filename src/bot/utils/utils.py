import json
import random
from string import ascii_letters, digits

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.callbacks_factory.factories import GetNextLyrics
from src.spotify.spotify import AsyncSpotify
from src.sql.models.session import Session


def generate_token(length) -> str:
    token = ''.join([random.choice(ascii_letters + digits) for _ in range(length)])
    return token


def update_admins(user_id, user_name):
    with open("../../../data/admins.json", 'r', encoding="utf-8") as file:
        before = json.load(file)
    before[str(user_id)] = user_name
    with open('../../../data/admins.json', 'w', encoding="utf-8") as file:
        file.write(json.dumps(before, indent=4, ensure_ascii=False))


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


async def get_menu_text(spotify: AsyncSpotify, session: Session, sql_session: AsyncSession):
    emoji_artists = '🥺🤫😐🙄😮😄😆🥹🙂😌😙😎😏🤩😋🥶🥵🤭🤔😈'
    curr_track = await spotify.get_curr_track()
    num_of_users = await session.users_num(sql_session)
    if curr_track is None:
        text = f'🔥 людей в сессии: {num_of_users}'
    else:
        volume = spotify.volume
        volume_str = f"{get_volume_emoji(volume)}: {volume}%\n\n" if spotify.is_playing else ""
        artists, name = curr_track
        text = (
                f"🎧: {name}\n\n{''.join(random.choices(emoji_artists, k=len(artists)))}️: {', '.join(artists)}\n\n" + volume_str +
                f"🔥 людей в сессии:"
                f" {num_of_users}")
    return text


# async def synchronize_queues(spotify_queue):
#     top_track = spotify_queue[0].id
#     ids = [item[1] for item in db.user_queue]
#     if top_track not in ids:
#         db.user_queue = []
#     else:
#         top_track_ind = ids.index(top_track)
#         db.user_queue = db.user_queue[top_track_ind:]


# TODO добавить возможность видеть кто поставил трек
async def get_queue_text(spotify: AsyncSpotify):
    queue = await spotify.get_curr_user_queue()
    queue = queue[0:min(len(queue), 10)]
    if len(queue) == 0:
        return None
    else:
        text = ""
        # ids = [item[1] for item in queue]
        for item in queue:
            # author = '' if item.id not in ids else (' - поставил(а) @' + db.users[db.user_queue[ids.index(item.id)][0]])
            author = ""
            text += (item.name[:item.name.find('(')] if '(' in item.name else item.name) + author + '\n\n'
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
