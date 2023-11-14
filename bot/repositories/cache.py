from typing import Any

import orjson as json
from pydantic import BaseModel

from .redis import RedisRepositoryBase


class CacheRepositoryBase(RedisRepositoryBase):
    model_cls: BaseModel

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