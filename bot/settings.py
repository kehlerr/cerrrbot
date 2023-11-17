import os

from decouple import config

from exceptions import InvalidSettingError


# Not app-specific settings
DEBUG = config("CERRRBOT_DEBUG", default=False, cast=bool)
SCHEME = config("CERRRBOT_HTTP_SCHEME", default="http" if DEBUG else "https").lower()
LOGGING_LEVEL = config("CERRRBOT_LOGGING_LEVEL", default="DEBUG" if DEBUG else "INFO").upper()

# Base app settings
BOT_TOKEN = config("CERRRBOT_TOKEN")
ALLOWED_USERS = config(
    "CERRRBOT_ALLOWED_USERS",
    cast=lambda v: [int(s.strip()) for s in v.split(",") if s],
    default="",
)
DATA_DIRECTORY_ROOT = config("CERRRBOT_DATA_ROOT", default=os.path.join(os.getcwd(), "appdata"))
if not os.path.isdir(DATA_DIRECTORY_ROOT):
    raise InvalidSettingError(f"CERRRBOT_DATA_ROOT doesn't exists: {DATA_DIRECTORY_ROOT}")
CUSTOM_MESSAGE_MIN_ORDER = config("CERRRBOT_CUSTOM_MESSAGE_MIN_ORDER", default=100, cast=int)

## Timeouts
DELETE_TIMEOUT_1 = config("CERRRBOT_DELETE_TIMEOUT_1", default=15, cast=int)
DELETE_TIMEOUT_2 = config("CERRRBOT_DELETE_TIMEOUT_2", default=30, cast=int)
DELETE_TIMEOUT_3 = config("CERRRBOT_DELETE_TIMEOUT_3", default=45, cast=int)
TIMEOUT_BEFORE_DEFAULT_ACTION_PERFORMS = config("CERRRBOT_TIMEOUT_BEFORE_DEFAULT_ACTION_PERFORMS", default=10, cast=int)
CHECK_NEW_MESSAGES_CD_PERIOD = config("CERRRBOT_CHECK_NEW_MESSAGES_CD_PERIOD", default=3, cast=int)
CHECK_DEPRECATED_MESSAGES_CD_PERIOD = config("CERRRBOT_CHECK_DEPRECATED_MESSAGES_CD_PERIOD", default=60, cast=int)

## Default cache settings
CACHE_DEFAULT_DB = config("CERRRBOT_CACHE_DEFAULT_DB", default=2, cast=int)
CACHE_DEFAULT_KEY_PREFIX = config("CERRRBOT_CACHE_DEFAULT_KEY_PREFIX", default="cerrrbot_cache")

## Notifications settings
NOTIFICATIONS_DB = config("CERRRBOT_NOTIFICATIONS_DB", default=3, cast=int)
NOTIFICATIONS_CACHE_KEY_PREFIX = config("CERRRBOT_NOTIFICATIONS_CACHE_KEY_PREFIX", default="cerrrbot_notification")
CHECK_NOTIFICATIONS_CD_PERIOD = config("CERRRBOT_CHECK_NOTIFICATIONS_CD_PERIOD", default=10, cast=int)

## Plugins settings
PLUGINS_MODULE_NAME = "plugins"
PLUGINS_DIR_PATH = os.path.join( os.path.dirname(os.path.realpath(__file__)), PLUGINS_MODULE_NAME)
if not os.path.isdir(PLUGINS_DIR_PATH):
    raise InvalidSettingError(f"PLUGINS_DIR_PATH doesn't exists: {PLUGINS_DIR_PATH}")

# MongoDB settings
MONGO_DB_HOST = config("CERRRBOT_MONGO_HOST", default="localhost")
MONGO_DB_PORT = config("CERRRBOT_MONGO_PORT", default=27017, cast=int)
MONGO_DB_NAME = config("CERRRBOT_MONGO_DB_NAME", default="cerrrbot_mongo")

# Redis settings
REDIS_HOST = config("CERRRBOT_REDIS_HOST", default="localhost")
REDIS_PORT = config("CERRRBOT_REDIS_PORT", default=6379, cast=int)

## Celery settings
CELERY_BROKER_DB = config("CERRRBOT_CELERY_BROKER_DB", default=0, cast=int)
CELERY_BACKEND_DB = config("CERRRBOT_CELERY_BACKEND_DB", default=1, cast=int)
