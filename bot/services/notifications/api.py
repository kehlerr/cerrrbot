import logging
from datetime import datetime
from uuid import uuid4

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from common import AppResult

from .notification import Notification
from .repository import get_repo

logger = logging.getLogger("cerrrbot")


async def push_message_notification(notification: Notification) -> AppResult:
    key = str(uuid4())
    repo = await get_repo()
    try:
        await repo.insert(key, notification)
    except Exception as exc:
        logger.exception(exc)
        return AppResult(False, exc)

    logger.info(f"Notification pushed: {key}")
    return AppResult()


async def process_notifications(bot: Bot):
    repo = await get_repo()
    notifications = await repo.get_all()
    for key, notification in notifications.items():
        logger.info(f"Got notification: {key}")
        if notification.need_send():
            result = await send_notification_message(bot, notification)
            if result and notification.need_repeat():
                result = await repeat_push(notification)
            if result:
                await repo.delete(key)


async def repeat_push(notification: Notification) -> AppResult:
    new_notificaton = notification.copy_with(
        send_at=int(datetime.utcnow().timestamp()) + notification.repeat_in,
        send_count=notification.send_count - 1,
    )
    result = await push_message_notification(new_notificaton)
    return result


async def send_notification_message(bot: Bot, notification: Notification) -> AppResult:
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
        return AppResult(False, exc)

    return AppResult
