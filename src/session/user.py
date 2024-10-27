class User:

    def __init__(self, user_id: int):
        self._user_id = user_id

    @property
    def user_id(self) -> int:
        return self._user_id


class TelegramUser(User):

    def __init__(self, user_id: int, username: str):
        super().__init__(user_id)
        self._username = username

    @property
    def username(self) -> str:
        return self._username
