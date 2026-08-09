from .logging import setup_logger
from .settings import app_settings


setup_logger(app_settings.logging_level, app_settings.logging_scope)


__all__ = ("app_settings",)
