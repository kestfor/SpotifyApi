from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.sql.models.user import User


async def handle_premium_required_error(callback: CallbackQuery | Message):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text='в меню', callback_data="menu"))
    if isinstance(callback, CallbackQuery):
        await callback.message.edit_text("Для этой функции требуется spotify premium",
                                         reply_markup=builder.as_markup())
    else:
        await callback.answer("Для этой функции требуется spotify premium", reply_markup=builder.as_markup())


async def handle_connection_error(callback: CallbackQuery | Message, user: User, bot=None):
    user_id = user.user_id
    text = 'ошибка соединения с Spotify 😞'
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="обновить", callback_data="refresh"))
    builder.row(InlineKeyboardButton(text='покинуть сессию', callback_data='leave_session'))
    if user.is_admin:
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
