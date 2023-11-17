from typing import Any

import orjson as json
from pydantic import BaseModel

from settings import CACHE_DEFAULT_DB, CACHE_DEFAULT_KEY_PREFIX

from .redis import RedisRepositoryBase


class CacheRepositoryBase(RedisRepositoryBase):
    model_cls: BaseModel

    DB_IDX = CACHE_DEFAULT_DB
    KEY_PREFIX = CACHE_DEFAULT_KEY_PREFIX

    async def select(self, key: str) -> Any:
        entry = await super().select(key)
        return self.model_load(entry)

    @classmethod
    def model_load(cls, data: bytes) -> Any:
        data = json.loads(data)
        return cls.model_cls(**data)

    @classmethod
    def _prepare_data(cls, data: Any) -> bytes:
        return json.dumps(data, default=cls.model_cls.dict)

    @staticmethod
    def model_dump(model_obj: Any) -> dict[str, Any]:
        return model_obj.json()