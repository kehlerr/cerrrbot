import os

from decouple import config

DEBUG = config("CERRRBOT_DEBUG", default=False, cast=bool)
if DEBUG:
    SCHEME = "http"
else:
    SCHEME = "https"

ALLOWED_USERS = config(
    "ALLOWED_USERS", cast=lambda v: [int(s.strip()) for s in v.split(",") if s], default=""
)

DATA_DIRECTORY_ROOT = config("DATA_DIRECTORY_ROOT", default="")

TOKEN = config("BOT_TOKEN")

OTP_SECRET_KEY = config("OTP_SECRET_KEY", default="")
PASS_STORE_DIR = config("PASS_STORE_DIR", default="")

MONGO_DB_HOST = config("MONGO_DB_HOST", default="localhost")
MONGO_DB_PORT = config("MONGO_DB_PORT", default=27017, cast=int)
MONGO_DB_NAME = config("MONGO_DB_NAME", default="cerrrbot_mongo")

REDIS_HOST = config("REDIS_HOST", default="localhost")
REDIS_PORT = config("REDIS_PORT", default=6379, cast=int)
REDIS_BROKER_DB_IDX = config("REDIS_BROKER_DB_IDX", default=0, cast=int)
REDIS_BACKEND_DB_IDX = config("REDIS_BACKEND_DB_IDX", default=1, cast=int)
REDIS_NOTIFICATIONS_DB_IDX = config("REDIS_BACKEND_DB_IDX", default=2, cast=int)

DELETE_TIMEOUT_1 = config("DELETE_TIMEOUT_1", default=15, cast=int)
DELETE_TIMEOUT_2 = config("DELETE_TIMEOUT_2", default=30, cast=int)
DELETE_TIMEOUT_3 = config("DELETE_TIMEOUT_3", default=45, cast=int)
DELETE_TIMEOUT_4 = config("DELETE_TIMEOUT_4", default=60, cast=int)
TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION = config(
    "TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION", default=5, cast=int
)

DEFAULT_CHECK_FOR_NEW_MESSAGES_TIMEOUT = config(
    "DEFAULT_CHECK_FOR_NEW_MESSAGES_TIMEOUT",
    default=5, cast=int
)

DEFAULT_CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT = config(
    "DEFAULT_CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT",
    default=5, cast=int
)


PLUGINS_MODULE_NAME = config(
    "PLUGINS_MODULE_NAME", default="plugins"
)

PLUGINS_DIR_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), PLUGINS_MODULE_NAME)