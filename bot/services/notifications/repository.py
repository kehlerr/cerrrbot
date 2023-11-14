
from repositories.cache import CacheRepositoryBase

from constants import CACHE_KEY_PREFIX_NOTIFICATION

from .notification import Notification


class NotificationRepository(CacheRepositoryBase):
    KEY_PREFIX = CACHE_KEY_PREFIX_NOTIFICATION
    model_cls = Notification


_repo: NotificationRepository | None = None


async def get_repo() -> NotificationRepository:
    global _repo
    if _repo is None:
        _repo = NotificationRepository()
        await _repo.init_client()
    return _repo