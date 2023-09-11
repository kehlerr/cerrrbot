import aioredis
import asyncio
import logging

from aioredis import RedisError

from settings import REDIS_HOST, REDIS_PORT, REDIS_NOTIFICATIONS_DB_IDX

logger = logging.getLogger(__name__)

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


async def push_message_notification(message_id: int, notification_data: dict) -> None:
    redis = await get_redis()
    data = json.dumps({"test": 123234, "ololo": "kek"})
    await redis.set(message_id, notification_data)
