from logging import getLogger
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message
from app.settings import ALLOWED_USERS


logger = getLogger("cerrrbot")


class CheckUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        message: Message,  # type: ignore
        data: dict[str, Any],
    ) -> Any:
        if (user_sender := message.from_user) and user_sender.id in ALLOWED_USERS:
            return await handler(message, data)

        logger.warning(
            "Someone tried to send message;\nUser: {};\nMessage: {}".format(
                user_sender, message
            )
        )
