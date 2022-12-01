from decouple import config

TOKEN = config("BOT_TOKEN")
OTP_SECRET_KEY = config("OTP_SECRET_KEY")

PASS_STORE_DIR = config("PASS_STORE_DIR")

MONGO_DB_HOST = config("MONGO_DB_HOST", default="localhost")
MONGO_DB_PORT = config("MONGO_DB_PORT", default=27017, cast=int)
MONGO_DB_NAME = config("MONGO_DB_NAME")
