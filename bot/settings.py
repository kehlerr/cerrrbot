import os

from decouple import config

DEBUG = config("CERRRBOT_DEBUG", default=False, cast=bool)
SCHEME = config(
    "CERRRBOT_HTTP_SCHEME",
    default="http" if DEBUG else "https"
).lower()
LOGGING_LEVEL = config(
    "CERRRBOT_LOGGING_LEVEL",
    default="DEBUG" if DEBUG else "INFO"
).upper()


ALLOWED_USERS = config(
    "ALLOWED_USERS", cast=lambda v: [int(s.strip()) for s in v.split(",") if s], default=""
)

DATA_DIRECTORY_ROOT = config("DATA_DIR_PATH", default=os.path.join(os.getcwd(), "appdata"))
assert os.path.isdir(DATA_DIRECTORY_ROOT), f"DATA_DIR_PATH doesn't exists: {DATA_DIRECTORY_ROOT}"

TOKEN = config("BOT_TOKEN")

MONGO_DB_HOST = config("CERRRBOT_MONGO_HOST", default="localhost")
MONGO_DB_PORT = config("CERRRBOT_MONGO_PORT", default=27017, cast=int)
MONGO_DB_NAME = config("CERRRBOT_MONGO_DB_NAME", default="cerrrbot_mongo")

REDIS_HOST = config("CERRRBOT_REDIS_HOST", default="localhost")
REDIS_PORT = config("CERRRBOT_REDIS_PORT", default=6379, cast=int)
REDIS_BROKER_DB_IDX = config("CERRRBOT_REDIS_BROKER_DB_IDX", default=0, cast=int)
REDIS_BACKEND_DB_IDX = config("CERRRBOT_REDIS_BACKEND_DB_IDX", default=1, cast=int)
REDIS_NOTIFICATIONS_DB_IDX = config("CERRRBOT_REDIS_BACKEND_DB_IDX", default=2, cast=int)

DELETE_TIMEOUT_1 = config("DELETE_TIMEOUT_1", default=15, cast=int)
DELETE_TIMEOUT_2 = config("DELETE_TIMEOUT_2", default=30, cast=int)
DELETE_TIMEOUT_3 = config("DELETE_TIMEOUT_3", default=45, cast=int)
TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION = config(
    "TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION", default=10, cast=int
)

DEFAULT_CHECK_FOR_NEW_MESSAGES_TIMEOUT = config(
    "DEFAULT_CHECK_FOR_NEW_MESSAGES_TIMEOUT",
    default=3, cast=int
)

DEFAULT_CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT = config(
    "DEFAULT_CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT",
    default=10, cast=int
)


PLUGINS_MODULE_NAME = config(
    "PLUGINS_MODULE_NAME", default="plugins"
)

DEFAULT_CACHE_KEY_PREFIX_NOTIFICATION = config("DEFAULT_CACHE_KEY_PREFIX_NOTIFICATION", default="cerrrbot_notification")


PLUGINS_DIR_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), PLUGINS_MODULE_NAME)
assert os.path.isdir(PLUGINS_DIR_PATH), f"PLUGINS_DIR_PATH doesn't exists: {PLUGINS_DIR_PATH}"