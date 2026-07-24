from logging import getLogger
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import ServerSelectionTimeoutError

from app.settings import MONGO_DB_HOST, MONGO_DB_NAME, MONGO_DB_PORT


logger = getLogger("cerrrbot")


async def check_connection() -> dict[str, Any] | None:
    client = _get_client()

    try:
        return await client.server_info()
    except ServerSelectionTimeoutError:
        return None
    finally:
        await client.close()


def get_mongo_db() -> AsyncDatabase:
    client = _get_client()
    return client[MONGO_DB_NAME]


def _get_client() -> AsyncMongoClient:

    logger.debug(f"Connecting to MongoDB host: {MONGO_DB_HOST}:{MONGO_DB_PORT}")

    return AsyncMongoClient(
        MONGO_DB_HOST,
        MONGO_DB_PORT,
        serverSelectionTimeoutMS=2000,
        connectTimeoutMS=15000,
    )
