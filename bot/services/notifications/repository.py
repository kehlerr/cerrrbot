
from repositories import CacheRepositoryBase

from constants import CACHE_KEY_PREFIX_NOTIFICATION, NOTIFICATIONS_DB_IDX

from .notification import Notification


class NotificationRepository(CacheRepositoryBase):
    model_cls = Notification

    DB_IDX = NOTIFICATIONS_DB_IDX
    KEY_PREFIX = CACHE_KEY_PREFIX_NOTIFICATION


_repo: NotificationRepository | None = None


async def get_repo() -> NotificationRepository:
    global _repo
    if _repo is None:
        _repo = NotificationRepository()
        await _repo.init_client()
    return _repo