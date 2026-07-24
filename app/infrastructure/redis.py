from redis import asyncio as aioredis

from app.settings import REDIS_HOST, REDIS_PORT, REDIS_DB


async def make_redis_client() -> aioredis.Redis:
    return await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
