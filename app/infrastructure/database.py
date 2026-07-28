from logging import getLogger
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import ServerSelectionTimeoutError

from .settings import infrastructure_settings

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
    return client[infrastructure_settings.mongo_db_name]


def _get_client() -> AsyncMongoClient:

    logger.debug(f"Connecting to MongoDB host: {infrastructure_settings.mongo_db_host}:{infrastructure_settings.mongo_db_port}")

    return AsyncMongoClient(
        infrastructure_settings.mongo_db_host,
        infrastructure_settings.mongo_db_port,
        serverSelectionTimeoutMS=2000,
        connectTimeoutMS=15000,
    )
