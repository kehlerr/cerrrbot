import logging
from uuid import uuid4

from aiogram import Bot

from common import AppResult
from constants import CACHE_KEY_PREFIX_NOTIFICATION
from repositories import cache

from .notification import Notification

logger = logging.getLogger("cerrrbot")


async def push_message_notification(notification: Notification) -> AppResult:
    key = f"{CACHE_KEY_PREFIX_NOTIFICATION}:{uuid4()}"
    try:
        client = await cache.get_client()
        await client.set(key, notification.model_dump())
    except Exception as exc:
        logger.exception(exc)
        return AppResult(False, exc)

    logger.info(f"Notification pushed: {key}")
    return AppResult()


async def process_notifications(bot: Bot):
    client = await cache.get_client()
    async for key in client.scan_iter(f"{CACHE_KEY_PREFIX_NOTIFICATION}:*"):
        logger.info(f"Got notification: {key}")
        notification_data = await client.get(key)
        notification = Notification.model_load(Notification, notification_data)
        result = await send_notification_message(bot, notification)
        if result:
            await client.delete(key)


async def send_notification_message(bot: Bot, notification: Notification) -> AppResult:
    try:
        await bot.send_message(
            chat_id=notification.chat_id,
            text=notification.text,
            reply_to_message_id=notification.reply_to_message_id
        )
    except Exception as exc:
        logger.exception(exc)
        return AppResult(False, exc)

    return AppResult
