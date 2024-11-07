from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.connect_user_to_session_route.connection_route import add_user_to_session_handler
from src.bot.spotify_sessions import spotify_sessions
from src.bot.start_arg import StartArg
from src.bot.utils.keyboards import get_menu_keyboard
from src.spotify.spotify import AsyncSpotify
from src.sql.models.user import User

router = Router()


async def default_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="начать сессию", callback_data='start_session'))
    builder.row(InlineKeyboardButton(text="присоединиться к сессии", callback_data='set_token'))
    builder.row(InlineKeyboardButton(text='привязать spotify аккаунт', callback_data='connect_spotify_account'))
    await message.answer(text="Spotify 🎧", reply_markup=builder.as_markup())


async def admin_start(message: Message, user: User):
    builder = InlineKeyboardBuilder()
    if user.in_session:
        await message.answer(text=f"сессия запущена 🔥\ntoken: <code>{user.token}</code>",
                             reply_markup=get_menu_keyboard(), parse_mode="HTML")
    else:
        builder.row(InlineKeyboardButton(text="начать сессию", callback_data='start_session'))
        await message.answer("Spotify 🎧", reply_markup=builder.as_markup())


async def user_start(message: Message):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="ввести токен", callback_data='set_token'))
    await message.answer("Spotify 🎧", reply_markup=builder.as_markup())


@router.message(Command("start"))
async def start_by_command(message: Message, command: CommandObject, state: FSMContext, user: User,
                           session: AsyncSession):
    start_arg = StartArg(command.args)
    match start_arg.type:
        case StartArg.Type.TOKEN | StartArg.Type.EMPTY:
            token = start_arg.value
            if token is None or token == '':
                await default_start(message)
            else:
                await add_user_to_session_handler(message, state, user, session, token)
        case StartArg.Type.AUTH:

            auth_hash = start_arg.value

            await user.add_auth(session, auth_hash)

            await admin_start(message, user)

    await message.delete()


@router.callback_query(F.data == 'start_session')
async def start_session(callback: CallbackQuery, user: User, session: AsyncSession):
    if not user.authorized:
        await callback.message.edit_text(
            f"Перейдите по ссылке для авторизации: {AsyncSpotify.create_authorize_route()}\n")
        return

    music_session = await user.create_session(session, str(user.user_id))
    await callback.message.edit_text(text=f"сессия запущена 🔥\n"
                                          f"token: <code>{music_session.token}</code>",
                                     reply_markup=get_menu_keyboard(),
                                     parse_mode="HTML")


@router.callback_query(F.data == "connect_spotify_account")
async def connect_spotify_account(callback: CallbackQuery, user: User, session: AsyncSession):
    if user.authorized:
        spotify = await spotify_sessions.get_or_create(user, session)
        spotify.deauthorize()
    await callback.message.edit_text(
        f"Перейдите по ссылке для авторизации: {AsyncSpotify.create_authorize_route()}\n")
    return
