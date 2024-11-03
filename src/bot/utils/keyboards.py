from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.sql.models.user import User


def get_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text='в меню', callback_data='menu'))
    return builder.as_markup()


def get_admin_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚙️ настройки ⚙️", callback_data="get_settings"))
    # builder.row(InlineKeyboardButton(text='🎵 добавить трек 🎵', callback_data='add_track'))
    builder.row(InlineKeyboardButton(text='💽 очередь 💽', callback_data="view_queue"))
    builder.row(InlineKeyboardButton(text='📖 текст песни 📖', callback_data="view_lyrics"))
    builder.row(InlineKeyboardButton(text='🔉', callback_data='decrease_volume'))
    builder.add(InlineKeyboardButton(text='🔇', callback_data='mute_volume'))
    builder.add(InlineKeyboardButton(text='🔊', callback_data="increase_volume"))
    builder.row(InlineKeyboardButton(text="🔄 обновить 🔄", callback_data='refresh'))
    builder.row(InlineKeyboardButton(text="⏮", callback_data="previous_track"))
    builder.add(InlineKeyboardButton(text="⏯", callback_data="start_pause"))
    builder.add(InlineKeyboardButton(text="⏭", callback_data="next_track"))
    return builder.as_markup()


def get_settings_keyboard(user: User):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="посмотреть токен", callback_data="view_token"))
    builder.row(InlineKeyboardButton(text='ссылка приглашение', callback_data="view_url"))
    builder.row(InlineKeyboardButton(text='QR-код', callback_data="view_qr"))
    builder.row(InlineKeyboardButton(text="сменить устройство", callback_data="view_devices"))
    if user.is_admin:
        builder.row(InlineKeyboardButton(text='изменить режим', callback_data="change_mode"))
        # builder.row(InlineKeyboardButton(text='добавить админа', callback_data="view_admins_to_add"))
    builder.row(InlineKeyboardButton(text='покинуть сессию', callback_data="leave_session"))
    if user.is_admin:
        builder.row(InlineKeyboardButton(text="завершить сессию", callback_data="confirm_end_session"))
    builder.row(InlineKeyboardButton(text='назад', callback_data="menu"))
    return builder.as_markup()


def get_user_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚙️ настройки ⚙️", callback_data="get_settings"))
    #builder.row(InlineKeyboardButton(text='🎵 добавить трек 🎵', callback_data="add_track"))
    builder.row(InlineKeyboardButton(text='💽 очередь 💽', callback_data="view_queue"))
    builder.row(InlineKeyboardButton(text='📖 текст песни 📖', callback_data="view_lyrics"))
    # if db.mode == db.share_mode:
    builder.row(InlineKeyboardButton(text='🔉', callback_data='decrease_volume'))
    builder.add(InlineKeyboardButton(text='🔇', callback_data='mute_volume'))
    builder.add(InlineKeyboardButton(text='🔊', callback_data="increase_volume"))
    builder.row(InlineKeyboardButton(text="🔄обновить🔄", callback_data='refresh'))
    # if db.mode == db.share_mode:
    builder.row(InlineKeyboardButton(text="⏮", callback_data="previous_track"))
    builder.add(InlineKeyboardButton(text="⏯", callback_data="start_pause"))
    builder.add(InlineKeyboardButton(text="⏭", callback_data="next_track"))
    return builder.as_markup()
