from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.spotify_sessions import spotify_sessions
from src.bot.states import SetTokenState
from src.bot.utils.keyboards import get_user_menu_keyboard
from src.bot.utils.utils import get_menu_text
from src.sql.models.session import Session
from src.sql.models.user import User

router = Router()


@router.callback_query(F.data == 'set_token')
async def set_user_token(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("введите токен")
    await state.set_state(SetTokenState.add_user)


@router.message(F.text.len() > 0, SetTokenState.add_user)
async def add_user_to_session_handler(message: Message, state: FSMContext, user: User, session: AsyncSession,
                                      token=None):
    token = message.text if token is None else token
    music_session = await Session.get_by_id(session, int(token))
    if music_session:
        await user.add_to_session(session, music_session.id)
        spotify = await spotify_sessions.get_or_create(user, session)
        await message.answer(text=await get_menu_text(spotify, user.session, session),
                             reply_markup=get_user_menu_keyboard())
        await message.delete()
        await state.clear()
    else:
        await message.answer(text='введен неверный токен или сессия не начата')
        await message.delete()
