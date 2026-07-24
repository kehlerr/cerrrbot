
from app.repositories import CachedModelRepository

from app.settings import NOTIFICATIONS_CACHE_KEY_PREFIX

from .notification import Notification


class NotificationRepository(CachedModelRepository):
    model_class = Notification

    KEY_PREFIX = NOTIFICATIONS_CACHE_KEY_PREFIX
