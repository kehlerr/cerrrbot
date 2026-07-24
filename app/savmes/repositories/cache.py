from app.models import MessageDocument
from app.repositories import RedisRepository


class SavmesCacheRepository(RedisRepository):

    KEY_PREFIX="svm"

    async def is_subsequent_in_media_group(self, media_group_id: str | None) -> bool:
        if not media_group_id:
            return False

        is_first_in_media_group = bool(await self.setnx(f"media_group_id:{media_group_id}", True, ttl=3600))
        return not is_first_in_media_group
