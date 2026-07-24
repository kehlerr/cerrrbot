import logging
from datetime import datetime, UTC
from uuid import uuid4

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from app.exceptions import AppError

from .exceptions import PushNotificationError, SendNotificationMessageError
from .notification import Notification
from .repository import NotificationRepository

logger = logging.getLogger("cerrrbot")


class NotificationService:
    def __init__(self, notification_repository: NotificationRepository) -> None:
        self._repo = notification_repository

    async def process_notifications(self, bot: Bot) -> None:
        async for key, notification in self._repo.iter_all():
            await self._process_notification(key, notification, bot)

    async def _process_notification(self, key: str, notification: Notification, bot: Bot) -> None:
        logger.debug(f"Got notification: {key}")

        if notification.need_send():
            await self.send_notification_message(bot, notification)

            if notification.need_repeat():
                await self.repeat_push(notification)

            await self._repo.delete(key)

    async def send_notification_message(self, bot: Bot, notification: Notification) -> None:
        try:
            await bot.send_message(
                chat_id=notification.chat_id,
                text=notification.text,
                reply_to_message_id=notification.reply_to_message_id,
            )
        except TelegramBadRequest:
            await bot.send_message(chat_id=notification.chat_id, text=notification.text)
        except Exception as exc:
            logger.exception(exc)
            raise SendNotificationMessageError(notification=notification)

    async def repeat_push(self, notification: Notification) -> None:
        send_count = notification.send_count - 1 if notification.send_count > 0 else notification.send_count
        new_notificaton = notification.model_copy(
            update = {
                "send_at": int(datetime.now(tz=UTC).timestamp()) + notification.repeat_in,
                "send_count": send_count
            },
            deep=True
        )
        await self.push_message_notification(new_notificaton)

    async def push_message_notification(self, notification: Notification) -> None:
        key = str(uuid4())
        try:
            await self._repo.insert(key, notification)
        except AppError as exc:
            logger.exception("Error occured while inserting notification: %s", exc)
            raise PushNotificationError(key=key)

        logger.info(f"Notification pushed: {key}")
