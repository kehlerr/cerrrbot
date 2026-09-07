import asyncio
from typing import cast

import orjson as json

from app.infrastructure.repositories import RedisRepository


class SavmesCacheRepository(RedisRepository):
    KEY_PREFIX = "svm"

    async def register_media_group(
        self,
        media_group_id: str,
        chat_id: int | None = None,
        source_id: str | None = None,
        origin_date: int | None = None,
    ) -> bool:
        is_first_in_media_group = await self.setnx(f"media_group_id:{media_group_id}", True, ttl=3600)
        if is_first_in_media_group and chat_id and source_id and origin_date:
            origin_key = self._cls_key(f"origin:{chat_id}:{source_id}:{origin_date}")
            await self._client.set(origin_key, self._prepare_data(media_group_id), ex=60)
        return is_first_in_media_group

    async def find_companion_media_group(
        self,
        chat_id: int,
        source_id: str,
        origin_date: int,
    ) -> str | None:
        timestamps = (origin_date, origin_date - 1, origin_date + 1)

        async def _check() -> str | None:
            for t in timestamps:
                key = self._cls_key(f"origin:{chat_id}:{source_id}:{t}")
                raw = await self._client.get(key)
                if raw is not None:
                    try:
                        return cast(str, json.loads(raw))
                    except Exception:
                        return raw.decode() if isinstance(raw, bytes) else str(raw)
            return None

        if msgid := await _check():
            return msgid

        await asyncio.sleep(0.25)
        return await _check()

    async def is_subsequent_in_media_group(self, media_group_id: str | None) -> bool:
        if not media_group_id:
            return False

        return not await self.register_media_group(media_group_id)
