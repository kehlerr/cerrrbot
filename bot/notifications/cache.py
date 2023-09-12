import logging
from uuid import uuid4

from aiogram import Bot
from redis import asyncio as aioredis

from common import AppResult
from settings import REDIS_HOST, REDIS_PORT, REDIS_NOTIFICATIONS_DB_IDX

from .notification import Notificaiton

logger = logging.getLogger("cerrrbot")

_redis = None


async def get_redis():
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_NOTIFICATIONS_DB_IDX}")
    return _redis


async def close_redis():
    global _redis
    try:
        _redis.close()
        await _redis.wait_closed()
    except Exception:
        pass

    _redis = None


CACHE_KEY_PREFIX_NOTIFICATION = "notification"


async def push_message_notification(notification: Notificaiton) -> AppResult:
    key = f"{CACHE_KEY_PREFIX_NOTIFICATION}:{uuid4()}"
    try:
        redis = await get_redis()
        await redis.set(key, notification.model_dump())
    except Exception as exc:
        logger.exception(exc)
        return AppResult(False, exc)

    logger.info(f"Notification pushed: {key}")
    return AppResult()


async def process_notifications(bot: Bot):
    redis = await get_redis()
    async for key in redis.scan_iter(f"{CACHE_KEY_PREFIX_NOTIFICATION}:*"):
        logger.info(f"Got notification: {key}")
        notification_data = await redis.get(key)
        notification = Notificaiton.model_load(Notificaiton, notification_data)
        result = await send_notification_message(bot, notification)
        if result:
            await redis.delete(key)


async def send_notification_message(bot: Bot, notification: Notificaiton) -> AppResult:
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
