import asyncio

from aiogram import F, Bot
from aiogram.dispatcher.router import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.callbacks_factory.factories import GetNextLyrics, AddAdminFactory, ChangeDeviceFactory, \
    AddSongCallbackFactory
from src.bot.filters import UrlFilter
from src.bot.handlers.error_handlers.handlers import handle_connection_error, error_wrapper
from src.bot.spotify_sessions import spotify_sessions
from src.bot.utils.keyboards import get_menu_keyboard, get_admin_menu_keyboard, get_user_menu_keyboard, \
    get_settings_keyboard
from src.bot.utils.utils import get_menu_text, get_queue_text, get_curr_song_info, get_lyrics_switcher, \
    save_users_last_message_id
from src.spotify.spotify import AsyncSpotify
from src.spotify.spotify import ConnectionError
from src.sql.models.user import User

router = Router()


async def menu(callback: CallbackQuery, spotify: AsyncSpotify, user: User, session: AsyncSession):
    try:
        await spotify.update()
        text = await get_menu_text(spotify, user, session)
    except ConnectionError:
        await handle_connection_error(callback, user)
        return
    if user.is_admin:
        keyboard = get_admin_menu_keyboard()
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")
    else:
        keyboard = get_user_menu_keyboard()
        await callback.message.edit_text(text=text, reply_markup=keyboard, parse_mode="HTML")


async def refresh(callback: CallbackQuery, spotify: AsyncSpotify, user: User, session: AsyncSession):
    old_text = callback.message.text
    await spotify.update()
    curr_text = await get_menu_text(spotify, user, session)
    if old_text != curr_text:
        await menu(callback, spotify, user, session)
    else:
        await callback.answer()


@router.callback_query(F.data == 'view_queue')
@error_wrapper()
async def view_queue(callback: CallbackQuery, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    queue = await get_queue_text(spotify)
    if queue is None or len(queue) == 0:
        await callback.message.edit_text("в очереди нет треков", reply_markup=get_menu_keyboard())
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text='в меню', callback_data="menu")
        builder.adjust(1)
        await callback.message.edit_text("треки в очереди:\n\n" + queue, reply_markup=builder.as_markup())


@router.callback_query(F.data == 'view_lyrics')
async def view_lyrics(callback: CallbackQuery, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    try:
        if not await spotify.has_cached_lyrics():
            await callback.message.edit_text("Ищу текст песни, подождите чуток, текст сейчас появится 😉", reply_markup=get_menu_keyboard())
        lyrics = await spotify.get_lyrics()
    except:
        await callback.message.edit_text("не удалось найти текст", reply_markup=get_menu_keyboard())
    else:
        song_info = await get_curr_song_info(lyrics)
        await callback.message.edit_text(song_info + '\n'.join(lyrics.list_lyrics[0:16]),
                                         reply_markup=get_lyrics_switcher(0, 16, 16))


@router.callback_query(GetNextLyrics.filter(F.action == 'increment'))
async def next_part_lyrics(callback: CallbackQuery, callback_data: GetNextLyrics, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    lyrics = await spotify.get_lyrics()
    start_ind = callback_data.start_ind
    end_ind = min(start_ind + callback_data.step, len(lyrics.list_lyrics))
    end_ind_conv = end_ind if end_ind != len(lyrics.list_lyrics) else -1
    curr_song_info = await get_curr_song_info(lyrics)
    await callback.message.edit_text(text=curr_song_info + '\n'.join(lyrics.list_lyrics[start_ind:end_ind]),
                                     reply_markup=get_lyrics_switcher(start_ind, end_ind_conv, end_ind - start_ind))


@router.callback_query(GetNextLyrics.filter(F.action == 'decrement'))
async def previous_part_lyrics(callback: CallbackQuery, callback_data: GetNextLyrics, user: User,
                               session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    lyrics = await spotify.get_lyrics()
    start_ind = max(callback_data.start_ind, 0)
    end_ind = callback_data.step + start_ind
    curr_song_info = await get_curr_song_info(lyrics)
    await callback.message.edit_text(
        text=curr_song_info + '\n'.join(lyrics.list_lyrics[start_ind:end_ind]),
        reply_markup=get_lyrics_switcher(start_ind, end_ind, callback_data.step))


# TODO try to implement
@router.callback_query(F.data == 'view_admins_to_add')
async def view_admins_to_add(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    # for user_id, username in db.users:
    #   if user_id not in db.admins:
    #      builder.button(text=username, callback_data=AddAdminFactory(user_id=user_id, user_name=username))
    builder.button(text="назад", callback_data='menu')
    await callback.message.edit_text(text='выберите пользователя', reply_markup=builder.as_markup())


# TODO try to implement
@router.callback_query(AddAdminFactory.filter())
async def add_admin(callback: CallbackQuery, callback_data: AddAdminFactory, bot):
    # db.add_admin(callback_data.user_id, callback_data.user_name)
    await callback.message.edit_text(text='добавлен новый администратор', reply_markup=get_menu_keyboard())
    # users = set(db.users.keys())
    # users.remove(callback_data.user_id)
    # await update_menu_for_all_users(bot, users)


@router.callback_query(F.data == "refresh")
@error_wrapper()
async def refresh_callback(callback: CallbackQuery, session: AsyncSession, user: User):
    spotify = await spotify_sessions.get_or_create(user, session)
    await refresh(callback, spotify, user, session)


@router.callback_query(F.data == "menu")
async def menu_callback(callback: CallbackQuery, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    await menu(callback, spotify, user, session)


@router.callback_query(F.data == 'start_playlist')
async def start_playlist_callback(callback: CallbackQuery):
    await callback.message.edit_text("отправь ссылку на альбом/плейлист/артиста",
                                     reply_markup=get_menu_keyboard())


@router.message(UrlFilter())
async def chose_url_role(message: Message, state: FSMContext, user: User, session):
    await start_playlist(message, user, session)


@error_wrapper()
async def start_playlist(message: Message, user: User, session):
    spotify = await spotify_sessions.get_or_create(user, session)
    try:
        await spotify.start_playlist(message.text)
    except ValueError:
        await message.answer(
            "неверная ссылка, необходима ссылка на spotify контент в виде автора, плейлиста или альбома",
            reply_markup=get_menu_keyboard())
    else:
        await message.answer("плейлист успешно запущен", reply_markup=get_menu_keyboard())
    #await message.delete()


@router.callback_query(F.data == "view_devices")
@error_wrapper()
async def view_devices(callback: CallbackQuery, user: User, session):
    keyboard = InlineKeyboardBuilder()
    spotify = await spotify_sessions.get_or_create(user, session)
    devices = await spotify.get_devices()
    for device in devices:
        text = device.name
        text = '🟢 ' + text if device.is_active else '🔴 ' + text
        keyboard.button(text=text, callback_data=ChangeDeviceFactory(id=device.id, is_active=device.is_active))
    keyboard.adjust(1)
    keyboard.row(InlineKeyboardButton(text="назад", callback_data="get_settings"))
    await callback.message.edit_text(text="доступные устройства Spotify", reply_markup=keyboard.as_markup())


@router.callback_query(ChangeDeviceFactory.filter())
@error_wrapper()
async def transfer_playback(callback: CallbackQuery, callback_data: ChangeDeviceFactory, user: User, session):
    device_id = callback_data.id
    is_active = callback_data.is_active
    spotify = await spotify_sessions.get_or_create(user, session)
    if is_active:
        await callback.message.edit_text("данное устройство уже является текущим устройством воспроизведения",
                                         reply_markup=get_menu_keyboard())
        return
    try:
        await spotify.transfer_player(device_id)
    except ConnectionError:
        await callback.message.edit_text("не удалось изменить устройство", reply_markup=get_menu_keyboard())
    else:
        await callback.message.edit_text("устройство воспроизведения успешно изменено",
                                         reply_markup=get_menu_keyboard())


# TODO check is needed to implement
# @router.callback_query(F.data != "start_session")
# async def handle_not_active_session(callback: CallbackQuery, user: User):
#     if user.is_admin:
#         await callback.message.edit_text("сессия завершена, для запуска сессии используйте команду '/start'",
#                                          reply_markup=None)
#     else:
#         await callback.message.edit_text("сессия завершена, обратитесь к админам для ее запуска")
#     await asyncio.sleep(5)
#     await callback.message.delete()


@router.callback_query(F.data == 'change_mode')
async def change_mode(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='share ♻️', callback_data="set_share_mode"))
    builder.row(InlineKeyboardButton(text='restricted 🔒', callback_data='set_restricted_mode'))
    await callback.message.edit_text(text='выберите режим', reply_markup=builder.as_markup())


# TODO implement if needed
@router.callback_query(F.data == 'set_share_mode')
async def set_share_mode(callback: CallbackQuery):
    await callback.message.edit_text(text='установлен режим share ♻️', reply_markup=get_menu_keyboard())


# TODO implement if needed
@router.callback_query(F.data == 'set_restricted_mode')
async def set_share_mode(callback: CallbackQuery):
    await callback.message.edit_text(text='установлен режим share restricted 🔒', reply_markup=get_menu_keyboard())


@router.callback_query(F.data == 'get_settings')
async def get_settings(callback: CallbackQuery, user):
    await callback.message.edit_text(text='⚙️ настройки ⚙️',
                                     reply_markup=get_settings_keyboard(user))


@router.callback_query(F.data == "add_track")
async def search_track_callback(callback: CallbackQuery):
    await callback.message.edit_text("введите поисковой запрос 🔎",
                                     reply_markup=get_menu_keyboard())


@router.message(F.text)
@error_wrapper()
@save_users_last_message_id()
async def search_track_handler(message: Message, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    list_of_results = await spotify.search(message.text)
    keyboard = InlineKeyboardBuilder()
    request = {}
    for item in list_of_results:
        song_info = ' - '.join(item[0:2])
        raw_uri = item[-1]
        request[raw_uri] = song_info
        keyboard.button(text=song_info, callback_data=AddSongCallbackFactory(uri=raw_uri))
    keyboard.adjust(1)
    keyboard.row(InlineKeyboardButton(text='назад', callback_data='menu'))
    msg = await message.answer("выберите результат поиска 😊", reply_markup=keyboard.as_markup())
    await message.delete()
    return msg


@router.callback_query(AddSongCallbackFactory.filter())
@error_wrapper()
async def add_song_to_queue(callback: CallbackQuery, callback_data: AddSongCallbackFactory, user: User, session):
    raw_uri = callback_data.uri
    spotify = await spotify_sessions.get_or_create(user, session)
    await spotify.add_track_to_queue(user.username, raw_uri)
    await callback.message.edit_text("трек добавлен в очередь 👌", reply_markup=get_menu_keyboard())


@router.callback_query(F.data == 'start_pause')
@error_wrapper()
async def start_pause_track(callback: CallbackQuery, bot: Bot, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    try:
        await spotify.start_pause()
    except ConnectionError:
        pass
    await menu(callback, spotify, user, session)


@router.callback_query(F.data == 'next_track')
@error_wrapper()
async def next_track(callback: CallbackQuery, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    old_track = await spotify.get_curr_track_data()
    await spotify.next_track()
    while old_track == await spotify.get_curr_track_data():
        await asyncio.sleep(0.5)
        await spotify.force_update()
    await menu(callback, spotify, user, session)


@router.callback_query(F.data == 'previous_track')
@error_wrapper()
async def previous_track(callback: CallbackQuery, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    old_track = await spotify.get_curr_track_data()
    await spotify.previous_track()
    while old_track == await spotify.get_curr_track_data():
        await asyncio.sleep(0.5)
        await spotify.force_update()
    await menu(callback, spotify, user, session)


@router.callback_query(F.data == 'confirm_end_session')
async def confirm_end_session(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅", callback_data="end_session"))
    builder.add(InlineKeyboardButton(text='❎', callback_data="menu"))
    await callback.message.edit_text(text="вы действительно хотите завершить сессию?",
                                     reply_markup=builder.as_markup())


@router.callback_query(F.data == 'end_session')
async def end_session(callback: CallbackQuery, user: User, session: AsyncSession):
    users = await user.session.get_users(session)
    for user in users:
        await spotify_sessions.clear_spotify(user)
    await user.session.delete(session)
    await callback.message.edit_text(
        text='сессия завершена, для начала новой используйте команду "/start"',
        reply_markup=None)
    await asyncio.sleep(3)
    #await callback.message.delete()


@router.callback_query(F.data == 'increase_volume')
@error_wrapper()
async def increase_volume(callback: CallbackQuery, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    await spotify.increase_volume()
    await menu(callback, spotify, user, session)


@router.callback_query(F.data == 'decrease_volume')
@error_wrapper()
async def decrease_volume(callback: CallbackQuery, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    await spotify.decrease_volume()
    await menu(callback, spotify, user, session)


@router.callback_query(F.data == 'mute_volume')
@error_wrapper()
async def mute_volume(callback: CallbackQuery, user: User, session: AsyncSession):
    spotify = await spotify_sessions.get_or_create(user, session)
    await spotify.mute_unmute()
    await menu(callback, spotify, user, session)


@router.callback_query(F.data == 'leave_session')
async def leave_session(callback: CallbackQuery, user: User, session: AsyncSession):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅", callback_data="confirm_leave_session"))
    builder.add(InlineKeyboardButton(text='❎', callback_data="menu"))
    if not user.is_admin or (await user.users_in_session_num(session)) > 1:
        await callback.message.edit_text(text='Вы уверены, что хотите покинуть сессию?',
                                         reply_markup=builder.as_markup())
    else:
        await confirm_end_session(callback)


@router.callback_query(F.data == "confirm_leave_session")
async def confirm_leave_session(callback: CallbackQuery, user: User, session: AsyncSession):
    await user.leave_session(session)
    await callback.message.edit_text(text='вы покинули сессию')
    await asyncio.sleep(3)
   # await callback.message.delete()
