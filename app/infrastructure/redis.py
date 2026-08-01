from redis import asyncio as aioredis

from .settings import infrastructure_settings


async def make_redis_client() -> aioredis.Redis:
    return await aioredis.from_url(infrastructure_settings.redis_client_url, decode_responses=True)
