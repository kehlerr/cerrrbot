import os
from enum import StrEnum
from typing import Any, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.exceptions import InvalidSettingError


class BotMode(StrEnum):
    AUTO = "auto"
    WEBHOOK = "webhook"
    POLLING = "polling"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CERRRBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base app settings
    debug: bool = Field(default=False)
    http_scheme: str = Field(default="http")
    logging_level: str = Field(default="DEBUG" if debug else "INFO")

    max_load_file_size: int = Field(default=20_000_000)

    # Bot app-related settings
    allowed_users: tuple[int, ...] = Field(default_factory=tuple)
    data_root: str = Field(default_factory=lambda: os.path.join(os.getcwd(), "appdata"))
    custom_message_min_order: int = 100

    # Timeouts
    delete_timeout_1: int = 15
    delete_timeout_2: int = 30
    delete_timeout_3: int = 45
    timeout_before_default_action_performs: int = 10
    check_new_messages_cd_period: int = 3
    check_deprecated_messages_cd_period: int = 60

    # Default cache settings
    cache_default_db: int = 2
    cache_default_key_prefix: str = "cerrrbot_cache"

    # Notifications settings
    notifications_db: int = 3
    notifications_cache_key_prefix: str = "cerrrbot_notification"
    check_notifications_cd_period: int = 10

    # MongoDB settings
    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_db_name: str = "cerrrbot_mongo"

    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 1

    # Celery settings
    celery_broker_db: int = 0
    celery_backend_db: int = 1

    @field_validator("allowed_users", mode="before")
    @classmethod
    def parse_allowed_users(cls, v: Any) -> tuple[int, ...]:
        if not v:
            return tuple()

        if isinstance(v, str):
            v_clean = v.strip("\"' ")
            return tuple(int(s.strip()) for s in v_clean.split(",") if s.strip())

        if isinstance(v, (list, tuple, set)):
            return tuple(int(x) for x in v)

        if isinstance(v, int):
            return (v,)

        raise InvalidSettingError(f"Invalid value for allowed users: {v}")

    @model_validator(mode="after")
    def compute_defaults_and_validate_paths(self) -> Self:
        if not self.http_scheme:
            self.http_scheme = "http" if self.debug else "https"
        else:
            self.http_scheme = self.http_scheme.lower()

        if not self.logging_level:
            self.logging_level = "DEBUG" if self.debug else "INFO"
        else:
            self.logging_level = self.logging_level.upper()

        if not os.path.isdir(self.data_root):
            raise InvalidSettingError(f"CERRRBOT_DATA_ROOT doesn't exists: {self.data_root}")

        plugins_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "plugins")
        if not os.path.isdir(plugins_dir):
            raise InvalidSettingError(f"PLUGINS_DIR_PATH doesn't exists: {plugins_dir}")

        return self


settings = Settings()  # type: ignore[call-arg]

# Re-export legacy settings constants for backwards compatibility
DEBUG = settings.debug
SCHEME = settings.http_scheme
LOGGING_LEVEL = settings.logging_level

ALLOWED_USERS = settings.allowed_users
MAX_LOAD_FILE_SIZE = settings.max_load_file_size
DATA_DIRECTORY_ROOT = settings.data_root
CUSTOM_MESSAGE_MIN_ORDER = settings.custom_message_min_order

DELETE_TIMEOUT_1 = settings.delete_timeout_1
DELETE_TIMEOUT_2 = settings.delete_timeout_2
DELETE_TIMEOUT_3 = settings.delete_timeout_3
TIMEOUT_BEFORE_DEFAULT_ACTION_PERFORMS = settings.timeout_before_default_action_performs
CHECK_NEW_MESSAGES_CD_PERIOD = settings.check_new_messages_cd_period
CHECK_DEPRECATED_MESSAGES_CD_PERIOD = settings.check_deprecated_messages_cd_period

CACHE_DEFAULT_DB = settings.cache_default_db
CACHE_DEFAULT_KEY_PREFIX = settings.cache_default_key_prefix

NOTIFICATIONS_DB = settings.notifications_db
NOTIFICATIONS_CACHE_KEY_PREFIX = settings.notifications_cache_key_prefix
CHECK_NOTIFICATIONS_CD_PERIOD = settings.check_notifications_cd_period

PLUGINS_MODULE_NAME = "plugins"
PLUGINS_DIR_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), PLUGINS_MODULE_NAME)

MONGO_DB_HOST = settings.mongo_host
MONGO_DB_PORT = settings.mongo_port
MONGO_DB_NAME = settings.mongo_db_name

REDIS_HOST = settings.redis_host
REDIS_PORT = settings.redis_port
REDIS_DB = settings.redis_db

CELERY_BROKER_DB = settings.celery_broker_db
CELERY_BACKEND_DB = settings.celery_backend_db
