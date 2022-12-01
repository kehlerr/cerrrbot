import logging
import bson
from typing import Any, Dict, List, Optional, Union

import pymongo
from pymongo.errors import ServerSelectionTimeoutError

from common import AppResult
from settings import MONGO_DB_HOST, MONGO_DB_NAME, MONGO_DB_PORT

logger = logging.getLogger(__name__)


class CollectionModel:
    name: str
    ttl: Optional[int] = 0

    @classmethod
    def add_document(cls, entry_data: Dict[str, Any]):
        return add_document(cls.name, entry_data)

    @classmethod
    def update_document(cls, entry_id: str, new_values: Dict[str, Any]) -> AppResult:
        db = get_mongo_db()
        collection = db[cls.name]

        if new_values:
            try:
                _id = bson.objectid.ObjectId(entry_id)
            except bson.errors.InvalidId:
                _id = entry_id

            try:
                result = collection.update_one({"_id": _id}, {"$set": new_values})
            except Exception as exc:
                return AppResult(False, exc)

            if result.modified_count != 1:
                return AppResult(False, "None of documents not modified")

        return AppResult(True)


class NewMessagesCollection(CollectionModel):
    name = "new_messages"


class SavedMessagesCollection(CollectionModel):
    name = "saved_messages"

    @classmethod
    def add_document(cls, entry_data: Dict[str, Any]) -> AppResult:
        if not entry_data.get("_id"):
            return AppResult(
                False, "Invalid new entry_data, missed _id field:{}".format(entry_data)
            )

        return super().add_document(entry_data)


def init_db():
    logger.info("Starting init DB...")
    db = get_mongo_db()
    existing_collections = db.list_collection_names()
    if existing_collections:
        logger.warning(
            "DB already initialized with next collections:{}".format(
                existing_collections
            )
        )
        return

    for collection_config in {SavedMessagesCollection, NewMessagesCollection}:
        db.create_collection(collection_config.name)


def del_documents(
    collection_name: str, documents_id: Union[str, List[str]]
) -> AppResult:
    if isinstance(documents_id, str):
        documents_id = [documents_id]

    pass


def add_document(collection_name: str, entry_data: Dict[str, Any]) -> AppResult:
    db = get_mongo_db()
    collection = db[collection_name]

    try:
        result = collection.insert_one(entry_data).inserted_id
    except Exception as exc:
        return AppResult(False, exc)

    return AppResult(True, data=result)


def check_connection() -> bool:
    client = _get_client()

    try:
        return client.server_info()
    except ServerSelectionTimeoutError:
        return False


def get_mongo_db():
    client = _get_client()
    return client[MONGO_DB_NAME]


def _get_client():
    return pymongo.MongoClient(
        MONGO_DB_HOST,
        MONGO_DB_PORT,
        serverSelectionTimeoutMS=15,
        connectTimeoutMS=15000,
    )
