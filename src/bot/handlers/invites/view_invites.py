import os

import qrcode
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.main_handlers.handlers import spotify_sessions
from src.bot.utils.keyboards import get_admin_menu_keyboard, get_user_menu_keyboard
from src.bot.utils.utils import get_menu_text
from src.sql.models.user import User

router = Router()


@router.callback_query(F.data == 'view_token')
async def view_token(callback: CallbackQuery, user: User, session: AsyncSession):
    master = await user.get_admin(session)
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="назад", callback_data="get_settings"))
    await callback.message.edit_text(f"token: <code>{master.token}</code>", reply_markup=builder.as_markup(),
                                     parse_mode="HTML")


@router.callback_query(F.data == 'view_qr')
async def view_qr(callback: CallbackQuery, bot: Bot, user: User, session: AsyncSession):
    master = await user.get_admin(session)
    url = f"t.me/SpotifyShareControlBot?start=_token_{master.token}"
    img = qrcode.make(url)
    img.save("qr_token")
    document = FSInputFile("qr_token")
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="в меню", callback_data="back_from_qr"))
    await bot.send_photo(photo=document, chat_id=callback.from_user.id,
                         reply_markup=builder.as_markup())
    await callback.message.delete()
    os.remove("qr_token")


@router.callback_query(F.data == 'back_from_qr')
async def back_from_qr(callback: CallbackQuery, bot: Bot, session: AsyncSession, user: User):
    spotify = await spotify_sessions.get_or_create(user, session)
    text = await get_menu_text(spotify, user.session, session)
    if user.is_admin:
        markup = get_admin_menu_keyboard()
    else:
        markup = get_user_menu_keyboard()
    await bot.send_message(text=text, chat_id=user.user_id, reply_markup=markup)
    await callback.message.delete()


@router.callback_query(F.data == 'view_url')
async def view_url(callback: CallbackQuery, user: User, session: AsyncSession):
    master = await user.get_admin(session)
    url = f"t.me/SpotifyShareControlBot?start=_token_{master.token}"
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="назад", callback_data="get_settings"))
    await callback.message.edit_text(text=url, reply_markup=builder.as_markup())
