from typing import Any, AsyncIterator, cast

from redis.asyncio.client import Redis


from app import app_settings

from app.types import TPydanticModel, PydanticModelClass

from .redis import RedisRepository



class CachedModelRepository[TPydanticModel]:
    model_class: type[TPydanticModel]

    KEY_PREFIX = app_settings.cache_default_key_prefix

    def __init__(self, redis_client: Redis, model_class: type[TPydanticModel] | None = None) -> None:
        self._redis_repository = RedisRepository(redis_client, key_prefix=self.KEY_PREFIX)
        self._model_class = cast(PydanticModelClass[TPydanticModel], model_class or self.model_class)

    async def iter_all(self, key_pattern: str | None = None, batch_size: int = 500) -> AsyncIterator[tuple[str, TPydanticModel]]:
        async for key, entry_bytes in self._redis_repository.iter_all_raw(key_pattern, batch_size):
            if entry_bytes is not None:
                yield key, self.model_load(entry_bytes)

    async def insert(self, key: str, obj: TPydanticModel) -> None:
        payload = self.model_dump(obj)
        return await self._redis_repository.insert(key, payload)

    async def select(self, key: str) -> Any:
        entry = await self._redis_repository.select(key)
        return self.model_load(entry)

    async def delete(self, key: str) -> None:
        return await self._redis_repository.delete(key)

    def model_load(self, data: bytes) -> TPydanticModel:
        return self._model_class.model_validate(data)

    def model_dump(self, data: TPydanticModel) -> dict[str, Any]:
        return cast(PydanticModelClass[TPydanticModel], data).model_dump(
            by_alias=True, exclude_unset=True, exclude_none=True
        )

    def _prepare_data(self, data: TPydanticModel) -> bytes:
        return self._redis_repository._prepare_data(self.model_dump(data))
