from typing import Any, AsyncIterator

import orjson as json
from redis.asyncio import Redis

from .exceptions import DuplicatedEntryError, EntryNotFoundError


class RedisRepository:
    KEY_PREFIX: str
    KEY_PREFIX_DELIMITER: str = ":"

    BATCH_SIZE: int = 500

    def __init__(self, redis_client: Redis, key_prefix: str | None = None) -> None:
        self._client = redis_client
        self.KEY_PREFIX = key_prefix or self.KEY_PREFIX
        self.KEY_ALL = f"{self.KEY_PREFIX}{self.KEY_PREFIX_DELIMITER}*"

    # TODO: iterate all
    async def get_all(self, key_pattern: str | None = None) -> dict[str, bytes]:
        key_pattern = key_pattern or self.KEY_ALL
        result: dict[str, bytes] = {}
        async for key in self._client.scan_iter(key_pattern):
            entry = await self.select(key)
            result[key] = entry
        return result

    async def iter_all_raw(self, key_pattern: str | None = None, batch_size: int | None = None) -> AsyncIterator[tuple[str, bytes | None]]:
        key_pattern = key_pattern or self.KEY_ALL
        batch_keys: list[str] = []

        batch_size = batch_size or self.BATCH_SIZE

        async for key in self._client.scan_iter(key_pattern):
            batch_keys.append(key)

            if len(batch_keys) >= batch_size:
                values: list[bytes | None] = await self._client.mget(batch_keys)

                for key, value in zip(batch_keys, values, strict=True):
                    yield key, value

                batch_keys.clear()

        if batch_keys:
            values = await self._client.mget(batch_keys)
            for key, value in zip(batch_keys, values, strict=True):
                yield key, value

    async def select(self, key: str) -> bytes:
        if (result :=  await self._client.get(self._cls_key(key))) is None:
            raise EntryNotFoundError(key=key)
        return result

    async def insert(self, key: str, dumped: Any) -> None:
        key = self._cls_key(key)
        if not await self.setnx(key, dumped):
            raise DuplicatedEntryError(key=key)

    async def setnx(self, key: str, payload_data: Any, ttl: int | None = None) -> bool:
        key = self._cls_key(key)
        return await self._client.set(key, self._prepare_data(payload_data), ex=ttl, nx=True) or False

    async def update(self, key: str, data: dict[str, Any]) -> None:
        await self._client.set(self._cls_key(key), self._prepare_data(data), keepttl=True)

    @classmethod
    def _prepare_data(cls, data: Any) -> bytes:
        return json.dumps(data)

    async def pop(self, key: str) -> Any | None:
        key = self._cls_key(key)
        result = None
        try:
            result = await self.select(key)
        except EntryNotFoundError:
            return None

        await self.delete(key)
        return result

    async def delete(self, key: str) -> None:
        await self._client.delete(self._cls_key(key))

    def _cls_key(self, key: str) -> str:
        key_prefix_full = f"{self.KEY_PREFIX}{self.KEY_PREFIX_DELIMITER}"
        if not key.startswith(key_prefix_full):
            return f"{key_prefix_full}{key}"
        return key
