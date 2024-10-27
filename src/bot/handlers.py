import asyncio
import os

import qrcode
from aiogram import F, Bot
from aiogram.dispatcher.router import Router
from aiogram.filters import CommandObject
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from data_base import db
from filters import UrlFilter
from src.bot.callbacks_factory.factories import GetNextLyrics, AddAdminFactory, ChangeDeviceFactory, \
    AddSongCallbackFactory
from src.bot.error_handlers.handlers import handle_connection_error, handle_premium_required_error
from src.bot.utils.keyboards import get_menu_keyboard, get_admin_menu_keyboard, get_user_menu_keyboard, \
    get_settings_keyboard
from src.bot.utils.utils import get_menu_text, get_queue_text, get_curr_song_info, get_lyrics_switcher
from src.spotify.spotify import AsyncSpotify
from src.spotify.spotify import PremiumRequired, ConnectionError, Forbidden
from src.sql.models.user import User
from start_arg import StartArg
from states import SetTokenState, SetSpotifyUrl

router = Router()
spotify_sessions: dict[int, AsyncSpotify] = {}


async def default_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="начать сессию", callback_data='start_session'))
    builder.row(InlineKeyboardButton(text="присоединиться к сессии", callback_data='set_token'))
    await message.answer(text="Spotify 🎧", reply_markup=builder.as_markup())


async def admin_start(message: Message, user: User):
    builder = InlineKeyboardBuilder()
    if user.in_session:
        await message.answer(text=f"сессия запущена 🔥\ntoken: <code>{db.token}</code>",
                             reply_markup=get_menu_keyboard(), parse_mode="HTML")
    else:
        builder.row(InlineKeyboardButton(text="начать сессию", callback_data='start_session'))
        await message.answer("Spotify 🎧", reply_markup=builder.as_markup())


async def user_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="ввести токен", callback_data='set_token'))
    await message.answer("Spotify 🎧", reply_markup=builder.as_markup())


async def menu(callback: CallbackQuery, spotify: AsyncSpotify, user: User, sql_session: AsyncSession):
    try:
        await spotify.update()
        text = await get_menu_text(spotify, user.session, sql_session)
    except ConnectionError:
        await handle_connection_error(callback, user)
        return
    if user.is_admin:
        keyboard = get_admin_menu_keyboard()
        await callback.message.edit_text(text=text, reply_markup=keyboard)
    else:
        keyboard = get_user_menu_keyboard()
        await callback.message.edit_text(text=text, reply_markup=keyboard)


async def refresh(callback: CallbackQuery, spotify: AsyncSpotify, user: User, sql_session: AsyncSession):
    old_text = callback.message.text
    try:
        await spotify.update()
        curr_text = await get_menu_text(spotify, user.session, sql_session)
    except ConnectionError:
        await handle_connection_error(callback, user)
        return
    if old_text != curr_text:
        await menu(callback, spotify, user, sql_session)
    else:
        return


@router.callback_query(F.data == 'view_queue')
async def view_queue(callback: CallbackQuery, user: User):
    spotify = spotify_sessions[user.user_id]
    queue = await get_queue_text(spotify)
    if queue is None or len(queue) == 0:
        await callback.message.edit_text("в очереди нет треков", reply_markup=get_menu_keyboard())
    else:
        builder = InlineKeyboardBuilder()
        builder.button(text='в меню', callback_data="menu")
        builder.adjust(1)
        await callback.message.edit_text("треки в очереди:\n\n" + queue, reply_markup=builder.as_markup())


@router.callback_query(F.data == 'view_url')
async def view_url(callback: CallbackQuery):
    url = f"t.me/SpotifyShareControlBot?start=_token_{db.token}"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="назад", callback_data="get_settings"))
    await callback.message.edit_text(text=url, reply_markup=builder.as_markup())


@router.callback_query(F.data == 'view_lyrics')
async def view_lyrics(callback: CallbackQuery, user: User):
    spotify = spotify_sessions[user.user_id]
    try:
        lyrics = await spotify.get_lyrics(callback.message.edit_text,
                                          text="ищу текст песни\nподождите чуток\nтекст сейчас появится 😉",
                                          reply_markup=get_menu_keyboard())
    except ValueError:
        await callback.message.edit_text("не удалось найти текст", reply_markup=get_menu_keyboard())
    else:
        song_info = await get_curr_song_info(lyrics)
        await callback.message.edit_text(song_info + '\n'.join(lyrics.list_lyrics[0:16]),
                                         reply_markup=get_lyrics_switcher(0, 16, 16))


@router.callback_query(GetNextLyrics.filter(F.action == 'increment'))
async def next_part_lyrics(callback: CallbackQuery, callback_data: GetNextLyrics, user: User):
    spotify = spotify_sessions[user.user_id]
    lyrics = await spotify.get_lyrics()
    start_ind = callback_data.start_ind
    end_ind = min(start_ind + callback_data.step, len(lyrics.list_lyrics))
    end_ind_conv = end_ind if end_ind != len(lyrics.list_lyrics) else -1
    curr_song_info = await get_curr_song_info(lyrics)
    await callback.message.edit_text(text=curr_song_info + '\n'.join(lyrics.list_lyrics[start_ind:end_ind]),
                                     reply_markup=get_lyrics_switcher(start_ind, end_ind_conv, end_ind - start_ind))


@router.callback_query(GetNextLyrics.filter(F.action == 'decrement'))
async def previous_part_lyrics(callback: CallbackQuery, callback_data: GetNextLyrics, user: User):
    spotify = spotify_sessions[user.user_id]
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


@router.callback_query(F.data == 'view_qr')
async def view_qr(callback: CallbackQuery, bot: Bot):
    url = f"t.me/SpotifyShareControlBot?start={db.token}"
    img = qrcode.make(url)
    img.save("qr_token")
    document = FSInputFile("qr_token")
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="в меню", callback_data="back_from_qr"))
    await bot.send_photo(photo=document, chat_id=callback.from_user.id,
                         reply_markup=builder.as_markup())
    os.remove("qr_token")


@router.callback_query(F.data == 'back_from_qr')
async def back_from_qr(bot: Bot, sql_session: AsyncSession, user: User):
    spotify = spotify_sessions[user.user_id]
    text = await get_menu_text(spotify, user.session, sql_session)
    if user.is_admin:
        markup = get_admin_menu_keyboard()
    else:
        markup = get_user_menu_keyboard()
    await bot.send_message(text=text, chat_id=user.user_id, reply_markup=markup)


@router.callback_query(F.data == "refresh")
async def refresh_callback(callback: CallbackQuery, sql_session: AsyncSession, user: User):
    spotify = spotify_sessions[user.user_id]
    await refresh(callback, spotify, user, sql_session)


@router.callback_query(F.data == "menu")
async def menu_callback(callback: CallbackQuery, user: User, sql_session: AsyncSession):
    spotify = spotify_sessions[user.user_id]
    await menu(callback, spotify, user, sql_session)


@router.callback_query(F.data == 'start_playlist')
async def start_playlist_callback(callback: CallbackQuery):
    await callback.message.edit_text("отправь ссылку на альбом/плейлист/артиста",
                                     reply_markup=get_menu_keyboard())


@router.message(UrlFilter())
async def chose_url_role(message: Message, state: FSMContext, bot: Bot):
    st = await state.get_state()
    if st == SetSpotifyUrl.set_url:
        await set_spotify_url(message, state, bot)
    else:
        await start_playlist(message)


async def start_playlist(message: Message, user: User):
    spotify = spotify_sessions[user.user_id]
    try:
        await spotify.start_playlist(message.text)
    except ValueError:
        await message.answer(
            "неверная ссылка, необходима ссылка на spotify контент в виде автора, плейлиста или альбома",
            reply_markup=get_menu_keyboard())
    except ConnectionError:
        await handle_connection_error(message, user)
    except PremiumRequired:
        await handle_premium_required_error(message)
    else:
        await message.answer("плейлист успешно запущен", reply_markup=get_menu_keyboard())
    await message.delete()


@router.callback_query(F.data == "view_devices")
async def view_devices(callback: CallbackQuery, user: User):
    spotify = spotify_sessions[user.user_id]
    keyboard = InlineKeyboardBuilder()
    devices = await spotify.get_devices()
    for device in devices:
        text = device.name
        text = '🟢 ' + text if device.is_active else '🔴 ' + text
        keyboard.button(text=text, callback_data=ChangeDeviceFactory(id=device.id, is_active=device.is_active))
    keyboard.adjust(1)
    keyboard.row(InlineKeyboardButton(text="назад", callback_data="get_settings"))
    await callback.message.edit_text(text="доступные устройства Spotify", reply_markup=keyboard.as_markup())


@router.callback_query(ChangeDeviceFactory.filter())
async def transfer_playback(callback: CallbackQuery, callback_data: ChangeDeviceFactory, user: User):
    device_id = callback_data.id
    is_active = callback_data.is_active
    if is_active:
        await callback.message.edit_text("данное устройство уже является текущим устройством воспроизведения",
                                         reply_markup=get_menu_keyboard())
        return
    try:
        spotify = spotify_sessions[user.user_id]
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


@router.message(Command("start"))
async def start_by_command(message: Message, command: CommandObject, bot: Bot, user: User, sql_session: AsyncSession):
    start_arg = StartArg(command.args)
    match start_arg.type:
        case StartArg.Type.TOKEN | StartArg.Type.EMPTY:
            token = start_arg.value
            if token is None or token == '':
                await default_start(message)
            else:
                # TODO check what is it for
                await authorize(token, user.user_id, message.from_user.username, bot)
        case StartArg.Type.AUTH:

            # TODO check is spotify truly initialized here
            auth_id = start_arg.value

            await user.add_auth(sql_session, auth_id)

            spotify_sessions[user.user_id] = AsyncSpotify()
            await admin_start(message, user)

    await message.delete()


# TODO fix logic
@router.callback_query(F.data == 'start_session')
async def start_session(callback: CallbackQuery, bot: Bot, state: FSMContext, user: User, sql_session: AsyncSession):
    if user.is_admin not in spotify_sessions:
        master = await user.get_admin(sql_session)
        spotify_sessions[user.user_id] = spotify_sessions[master.user_id]
        spotify = spotify_sessions[user.user_id]
        await callback.message.edit_text(
            f"Перейдите по ссылке для авторизации: {await spotify.create_authorize_route()}\n")
        await state.set_state(SetSpotifyUrl.set_url)
        return

    msg = await callback.message.edit_text(text=f"сессия запущена 🔥\n"
                                                f"token: <code>{db.token}</code>", reply_markup=get_menu_keyboard(),
                                           parse_mode="HTML")

    # text = ('не удалось обнаружить активное устройство spotify 😞\n\n'
    #         'для обнаружения устройства:\n\n'
    #         '1) запустите приложение spotify и любой трек/альбом на устройстве, управление которым вы хотите '
    #         'осуществлять\n\n'
    #         '2) заново запустите сессию (/start)')
    # await callback.message.edit_text(text=text, reply_markup=None)

    # else:
    # db.set_token()
    # await db.include_update_functions([update_queue_for_all_users, update_menu_for_all_users], [[bot], [bot]])
    #
    # # db.update_last_message(callback.from_user.id, msg)


# TODO хз че там дальше еще не видел


@router.callback_query(F.data == 'view_token')
async def view_token(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="назад", callback_data="get_settings"))
    await callback.message.edit_text(f"token: <code>{db.token}</code>", reply_markup=builder.as_markup(),
                                           parse_mode="HTML")


@router.callback_query(F.data == 'set_token')
async def set_user_token(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("введите токен")
    await state.set_state(SetTokenState.add_user)


# TODO create user to session auth route
# async def authorize_new_user(token, user_id, user_name, bot: Bot):
#     if db.token == token:
#         # await db.del_last_message(user_id)
#         await asyncio.sleep(0.3)
#         db.add_user(user_id, user_name)
#         msg = await bot.send_message(text=await get_menu_text(), chat_id=user_id, reply_markup=get_user_menu_keyboard())
#     else:
#         # await db.del_last_message(user_id)
#         await asyncio.sleep(0.3)
#         msg = await bot.send_message(chat_id=user_id, text='введен неверный токен или сессия не начата')
#     # db.update_last_message(user_id, msg)


# @router.message(F.text.len() > 0, SetTokenState.add_user)
# async def add_user_to_session(message: Message, state: FSMContext):
#     token = message.text
#     user_name = message.from_user.username
#     user_id = message.from_user.id
#     if token:
#         # await db.del_last_message(user_id)
#         await asyncio.sleep(0.3)
#         db.add_user(user_id, user_name)
#         msg = await message.answer(text=await get_menu_text(), reply_markup=get_user_menu_keyboard())
#         await message.delete()
#         await state.clear()
#     else:
#         # await db.del_last_message(user_id)
#         await asyncio.sleep(0.3)
#         msg = await message.answer(text='введен неверный токен или сессия не начата')
#         await message.delete()
#     # db.update_last_message(user_id, msg)


@router.callback_query(F.data == "add_track")
async def search_track_callback(callback: CallbackQuery):
    await callback.message.edit_text("введите поисковой запрос 🔎",
                                               reply_markup=get_menu_keyboard())


@router.message(F.text)
async def search_track_handler(message: Message, user: User):
    spotify = spotify_sessions[user.user_id]
    if user.in_session:
        try:
            list_of_results = await spotify.search(message.text)
        except ConnectionError:
            await handle_connection_error(message, user)
            return
        keyboard = InlineKeyboardBuilder()
        request = {}
        for item in list_of_results:
            song_info = ' - '.join(item[0:2])
            raw_uri = item[-1]
            request[raw_uri] = song_info
            keyboard.button(text=song_info, callback_data=AddSongCallbackFactory(uri=raw_uri))
        keyboard.adjust(1)
        keyboard.row(InlineKeyboardButton(text='назад', callback_data='menu'))
        await message.answer("выберите результат поиска 😊", reply_markup=keyboard.as_markup())
        await message.delete()
    else:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text='ввести токен', callback_data="set_token"))
        await message.answer(text='необходимо подключиться к сессии ⌨️', reply_markup=builder.as_markup())
        await message.delete()


# TODO add song to queue
@router.callback_query(AddSongCallbackFactory.filter())
async def add_song_to_queue(callback: CallbackQuery, callback_data: AddSongCallbackFactory, user: User):
    raw_uri = callback_data.uri
    user_id = callback.from_user.id
    spotify = spotify_sessions[user_id]
    try:
        await spotify.add_track_to_queue(raw_uri)
    except PremiumRequired:
        await handle_premium_required_error(callback)
    except ConnectionError:
        await handle_connection_error(callback, user)
    else:
        await callback.message.edit_text("трек добавлен в очередь 👌", reply_markup=get_menu_keyboard())


@router.callback_query(F.data == 'start_pause')
async def start_pause_track(callback: CallbackQuery, bot: Bot, user: User, sql_session: AsyncSession):
    spotify = spotify_sessions[user.user_id]
    try:
        await spotify.start_pause()
    except PremiumRequired:
        await handle_premium_required_error(callback)
        return
    except ConnectionError:
        pass
    await menu(callback, spotify, user, sql_session)


@router.callback_query(F.data == 'next_track')
async def next_track(callback: CallbackQuery, bot: Bot):
    if not db.is_active():
        await handle_not_active_session(callback)
        return
    user_id = callback.from_user.id
    if user_id in db.admins or db.mode == db.share_mode:
        try:
            old_track = await spotify.get_curr_track()
            await spotify.next_track()
            while old_track == await spotify.get_curr_track():
                await asyncio.sleep(0.5)
                await spotify.force_update()
        except PremiumRequired:
            await handle_premium_required_error(callback)
            return
        except ConnectionError:
            pass
        await menu(callback)
        await update_menu_for_all_users(bot, callback.from_user.id)
        await update_queue_for_all_users(bot)


@router.callback_query(F.data == 'previous_track')
async def previous_track(callback: CallbackQuery, bot: Bot):
    if not db.is_active():
        await handle_not_active_session(callback)
        return
    user_id = callback.from_user.id
    if user_id in db.admins or db.mode == db.share_mode:
        try:
            old_track = await spotify.get_curr_track()
            await spotify.previous_track()
            while old_track == await spotify.get_curr_track():
                await asyncio.sleep(0.5)
                await spotify.force_update()
        except PremiumRequired:
            await handle_premium_required_error(callback)
            return
        except ConnectionError:
            pass
        await menu(callback)
        await update_menu_for_all_users(bot, callback.from_user.id)
        await update_queue_for_all_users(bot)


@router.callback_query(F.data == 'confirm_end_session')
async def confirm_end_session(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅", callback_data="end_session"))
    builder.add(InlineKeyboardButton(text='❎', callback_data="menu"))
    msg = await callback.message.edit_text(text="вы действительно хотите завершить сессию?",
                                           reply_markup=builder.as_markup())
    # db.update_last_message(callback.from_user.id, msg)


@router.callback_query(F.data == 'end_session')
async def end_session(callback: CallbackQuery, bot: Bot):
    for user in db.users:
        try:
            if user not in db.admins:
                msg = await bot.send_message(chat_id=user, text="сессия завершена, для ее начала обратитесь к админам",
                                             reply_markup=None)
            else:
                msg = await bot.send_message(chat_id=user,
                                             text='сессия завершена, для начала новой используйте команду "/start"',
                                             reply_markup=None)
            # await db.del_last_message(user)
            await del_message(msg)
        except:
            pass
    await spotify.close()
    db.clear()


@router.callback_query(F.data == 'increase_volume')
async def increase_volume(callback: CallbackQuery, bot: Bot):
    if not db.is_active():
        await handle_not_active_session(callback)
        return
    try:
        await spotify.increase_volume()
    except PremiumRequired:
        await handle_premium_required_error(callback)
        return
    except ConnectionError:
        pass
    await menu(callback)
    await update_menu_for_all_users(bot, callback.from_user.id)


@router.callback_query(F.data == 'decrease_volume')
async def decrease_volume(callback: CallbackQuery, bot: Bot):
    if not db.is_active():
        await handle_not_active_session(callback)
        return
    try:
        await spotify.decrease_volume()
    except PremiumRequired:
        await handle_premium_required_error(callback)
        return
    except ConnectionError:
        pass
    await menu(callback)
    await update_menu_for_all_users(bot, callback.from_user.id)


@router.callback_query(F.data == 'mute_volume')
async def mute_volume(callback: CallbackQuery, bot: Bot):
    if not db.is_active():
        await handle_not_active_session(callback)
        return
    try:
        await spotify.mute_unmute()
    except PremiumRequired:
        await handle_premium_required_error(callback)
        return
    except ConnectionError:
        pass
    except Forbidden:
        pass
    await menu(callback)
    await update_menu_for_all_users(bot, callback.from_user.id)


@router.callback_query(F.data == 'leave_session')
async def leave_session(callback: CallbackQuery):
    user_id = callback.from_user.id
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅", callback_data="confirm_leave_session"))
    builder.add(InlineKeyboardButton(text='❎', callback_data="menu"))
    if user_id not in db.admins or len(db.admins) > 1:
        msg = await callback.message.edit_text(text='Вы уверены, что хотите покинуть сессию?',
                                               reply_markup=builder.as_markup())
        # db.update_last_message(user_id, msg)
    else:
        await confirm_end_session(callback)


@router.callback_query(F.data == "confirm_leave_session")
async def confirm_leave_session(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in db.admins:
        db.del_admin(user_id)
    if user_id in db.users:
        db.del_user(user_id)
    await callback.message.edit_text(text='вы покинули сессию')
    await asyncio.sleep(5)
    await callback.message.delete()
