from aiogram.types import Message


class UrlFilter:

    def __call__(self, message: Message):
        return message.text.startswith("http")
