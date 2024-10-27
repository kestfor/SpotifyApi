from src.session.user import TelegramUser
from src.spotify.spotify import AsyncSpotify
from src.sql.user import SQLSessionController


class MusicSession:

    def __init__(self, master: TelegramUser):
        self._master = master
        self._users: list[TelegramUser] = [self._master]
        self._spotify: AsyncSpotify = AsyncSpotify()
        self._db = SQLSessionController(int(self.id), str(self.id))
        # self._data_base: DataBase = DataBase(config.data_path)

    async def start(self, auth_id: int):
        await self._spotify.authorize(auth_id)
        await self._db.create()
        await self._db.add_user(self._master)

    @property
    def id(self):
        return self._master.user_id

    @property
    def users(self):
        return self._users

    @property
    def spotify(self):
        return self._spotify

    # @property
    # def data_base(self):
    #     return self._data_base
