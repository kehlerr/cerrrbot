from typing import Any

import orjson as json
from redis import asyncio as aioredis, Redis
from settings import REDIS_HOST, REDIS_NOTIFICATIONS_DB_IDX, REDIS_PORT

from .exceptions import DuplicatedEntryError, EntryNotFoundError

_redis = None


async def get_client(db_idx: int = REDIS_NOTIFICATIONS_DB_IDX) -> Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}/{db_idx}"
        )
    return _redis


class RedisRepositoryBase:
    KEY_PREFIX: str
    DB_IDX: int = 2
    KEY_PREFIX_DELIMITER: str = ":"

    def __init__(self) -> None:
        self._client: Redis | None = None
        self.KEY_ALL = f"{self.KEY_PREFIX}{self.KEY_PREFIX_DELIMITER}*"

    async def init_client(self) -> None:
        self._client = await get_client(self.DB_IDX)

    # TODO: iterate all
    async def get_all(self, key_pattern: str | None = None) -> dict[str, bytes]:
        key_pattern = key_pattern or self.KEY_ALL
        result: dict[str, bytes] = {}
        async for keyb in self._client.scan_iter(key_pattern):
            key = keyb.decode()
            entry = await self.select(key)
            result[key] = entry
        return result

    async def select(self, key: str) -> bytes:
        result = await self._client.get(self._cls_key(key))
        if result is None:
            raise EntryNotFoundError
        return result

    async def insert(self, key: str, data: dict[str, Any]) -> None:
        key = self._cls_key(key)
        data = self._prepare_data(data)
        result = await self._client.setnx(key, data)
        if not result:
            raise DuplicatedEntryError(f"Entry with key {key} already exists")

    async def update(self, key: str, data: dict[str, Any]) -> None:
        await self._client.set(self._cls_key(key), self._prepare_data(data))

    @classmethod
    def _prepare_data(cls, data: dict[str, Any]) -> bytes:
        return json.dumps(data)

    async def delete(self, key: str) -> None:
        await self._client.delete(self._cls_key(key))

    def _cls_key(cls, key: str) -> str:
        key_prefix_full = f"{cls.KEY_PREFIX}{cls.KEY_PREFIX_DELIMITER}"
        if not key.startswith(key_prefix_full):
            return f"{key_prefix_full}{key}"
        return key
