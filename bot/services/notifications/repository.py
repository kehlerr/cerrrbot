
from repositories import CacheRepositoryBase

from settings import NOTIFICATIONS_DB, NOTIFICATIONS_CACHE_KEY_PREFIX

from .notification import Notification


class NotificationRepository(CacheRepositoryBase):
    model_cls = Notification

    DB_IDX = NOTIFICATIONS_DB
    KEY_PREFIX = NOTIFICATIONS_CACHE_KEY_PREFIX


_repo: NotificationRepository | None = None


async def get_repo() -> NotificationRepository:
    global _repo
    if _repo is None:
        _repo = NotificationRepository()
        await _repo.init_client()
    return _repo