from aiogram.filters.callback_data import CallbackData


class AddSongCallbackFactory(CallbackData, prefix="fabAddSong"):
    uri: str


class ViewQueueFactory(CallbackData, prefix="fabViewQueue"):
    id: str


class ChangeSongsVote(CallbackData, prefix="fabAddVote"):
    uri: str
    action: str


class ChangeDeviceFactory(CallbackData, prefix="fabDevice"):
    id: str
    is_active: bool


class AddAdminFactory(CallbackData, prefix="addAdmin"):
    user_id: int
    user_name: str


class GetNextLyrics(CallbackData, prefix="fabLyrics", sep='~'):
    start_ind: int
    step: int
    action: str
