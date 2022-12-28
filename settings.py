from decouple import config

ALLOWED_USERS = config(
    "ALLOWED_USERS", cast=lambda v: [int(s.strip()) for s in v.split(",")]
)

DATA_DIRECTORY_ROOT = config("DATA_DIRECTORY_ROOT")

TOKEN = config("BOT_TOKEN")
OTP_SECRET_KEY = config("OTP_SECRET_KEY")

PASS_STORE_DIR = config("PASS_STORE_DIR")

MONGO_DB_HOST = config("MONGO_DB_HOST", default="localhost")
MONGO_DB_PORT = config("MONGO_DB_PORT", default=27017, cast=int)
MONGO_DB_NAME = config("MONGO_DB_NAME", default="cerrrbot_mongo")

DELETE_TIMEOUT_1 = config("DELETE_TIMEOUT_1", default=15, cast=int)
DELETE_TIMEOUT_2 = config("DELETE_TIMEOUT_2", default=30, cast=int)
DELETE_TIMEOUT_3 = config("DELETE_TIMEOUT_3", default=45, cast=int)
DELETE_TIMEOUT_4 = config("DELETE_TIMEOUT_4", default=60, cast=int)
TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION = config(
    "TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION", default=5 * 60, cast=int
)
