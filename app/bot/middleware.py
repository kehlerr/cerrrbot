from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message
from loguru import logger

from app import app_settings


class CheckUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        message: Message,  # type: ignore
        data: dict[str, Any],
    ) -> Any:
        if (user_sender := message.from_user) and user_sender.id in app_settings.allowed_users:
            return await handler(message, data)

        logger.warning(f"Someone tried to send message;\nUser: {user_sender};\nMessage: {message}")
