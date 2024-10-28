# from typing import Callable, Any, Awaitable
#
# from aiogram import BaseMiddleware
# from aiogram.types import TelegramObject
#
#
# class RetryMiddleware(BaseMiddleware):
#     def __init__(self, max_retries: int = 3, delay: float = 10):
#         self.max_retries = max_retries
#         self.delay = delay
#         self.retry_count = 0
#         self.exception_count: dict[str, int] = {}
#
#     async def __call__(
#             self,
#             handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
#             event: TelegramObject,
#             data: dict[str, Any],
#     ) -> Any:
#         retries = 0
#
#         while True:
#             try:
#                 return await handler(event, data)
#             except TelegramRetryAfter as e:
#                 logger.error(f"RETRY AFTER ERROR: {e.message}")
#                 await asyncio.sleep(e.retry_after)
#                 continue  # Retry the request after sleeping
#             except Exception as e:
#                 exception_class = e.__class__.__name__
#                 self.exception_count[exception_class] = self.exception_count.get(exception_class, 0) + 1
#                 logger.error(f'Handling {exception_class} in __call__')
#
#                 retries += 1
#                 self.retry_count += 1
#                 if retries >= self.max_retries:
#                     logger.error(f"Max retries ({self.max_retries}) reached. Raising exception...")
#                     raise e
#                 logger.warning(
#                     f"Encountered exception: {exception_class}. Retrying in {self.delay} seconds... (Retry {retries}/{self.max_retries})")
#                 await asyncio.sleep(self.delay)
