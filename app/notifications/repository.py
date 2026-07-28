from app import app_settings
from app.repositories import CachedModelRepository

from .notification import Notification


class NotificationRepository(CachedModelRepository):
    model_class = Notification

    KEY_PREFIX = app_settings.notifications_cache_key_prefix
