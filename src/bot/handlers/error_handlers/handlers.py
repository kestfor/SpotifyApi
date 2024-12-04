import functools

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.utils.keyboards import get_menu_keyboard
from src.spotify.spotify_errors import PremiumRequired, ConnectionError, UnsupportedDevice
from src.sql.models.user import User


def error_wrapper():
    def wrapper(function):
        @functools.wraps(function)
        async def wrapped(*args, **kwargs):
            res = None
            try:
                res = await function(*args, **kwargs)
            except PremiumRequired:
                arg1 = None
                for arg in args:
                    if isinstance(arg, CallbackQuery | Message):
                        arg1 = arg
                await handle_premium_required_error(arg1)
            except UnsupportedDevice:
                arg1 = None
                for arg in args:
                    if isinstance(arg, CallbackQuery):
                        arg1 = arg
                await handle_not_supported_device(arg1)
            except Exception:
                arg1 = arg2 = arg3 = None
                for arg in args:
                    if isinstance(arg, Message | CallbackQuery):
                        arg1 = arg
                    if isinstance(arg, User):
                        arg2 = arg
                    if isinstance(arg, Bot):
                        arg3 = arg
                await handle_connection_error(arg1, arg2, arg3)
            return res

        return wrapped

    return wrapper


async def handle_not_supported_device(callback: CallbackQuery):
    await callback.message.edit_text("текущее устройство воспроизведения не поддерживает данный функционал",
                                     reply_markup=get_menu_keyboard())


async def handle_premium_required_error(callback: CallbackQuery | Message):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='в меню', callback_data="menu"))
    if isinstance(callback, CallbackQuery):
        await callback.message.edit_text("Для этой функции требуется spotify premium",
                                         reply_markup=builder.as_markup())
    else:
        await callback.answer("Для этой функции требуется spotify premium", reply_markup=builder.as_markup())


async def handle_connection_error(callback: CallbackQuery | Message, user: User = None, bot=None):
    user_id = callback.from_user.id
    text = 'ошибка соединения с Spotify 😞\nпроверьте что запущено хотя бы одно устройство воспроизведения'
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="обновить", callback_data="refresh"))
    builder.row(InlineKeyboardButton(text='покинуть сессию', callback_data='leave_session'))
    if user is not None and user.is_master:
        builder.row(InlineKeyboardButton(text='завершить сессию', callback_data="confirm_end_session"))
    if bot is None:
        if isinstance(callback, CallbackQuery):
            await callback.message.edit_text(text=text, reply_markup=builder.as_markup())
        else:
            message = callback
            await message.answer(text=text, reply_markup=builder.as_markup())
    else:
        try:
            message = callback
            await bot.edit_message_text(chat_id=user_id, text=text, message_id=message.message_id,
                                        reply_markup=builder.as_markup())
        except:
            pass
