from loguru import logger
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import ServerSelectionTimeoutError

from .settings import infrastructure_settings


async def check_connection() -> bool:
    logger.info("Checking database connection...")

    client = _get_client()

    try:
        server_info = await client.server_info()
    except ServerSelectionTimeoutError:
        server_info = None
    finally:
        await client.close()

    if not server_info:
        logger.error("Failed to reach database.")
        return False

    logger.info("Database is reachable and online.")
    logger.debug(f"Database server info: {server_info}")

    return True


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
