
from redis import asyncio as aioredis

from settings import REDIS_HOST, REDIS_PORT, REDIS_NOTIFICATIONS_DB_IDX

_redis = None


async def get_client():
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_NOTIFICATIONS_DB_IDX}")
    return _redis
