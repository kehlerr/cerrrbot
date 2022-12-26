import logging
from typing import Any, Dict, List, Optional

import bson
import pymongo
from bson.objectid import ObjectId
from pymongo.errors import ServerSelectionTimeoutError

from common import AppResult
from settings import MONGO_DB_HOST, MONGO_DB_NAME, MONGO_DB_PORT

logger = logging.getLogger(__name__)


class CollectionModel:
    name: str
    ttl: Optional[int] = 0

    @classmethod
    def add_document(cls, entry_data: Dict[str, Any]) -> AppResult:
        return _add_document(cls.name, entry_data)

    @classmethod
    def update_document(cls, entry_id: str, new_values: Dict[str, Any]) -> AppResult:
        db = get_mongo_db()
        collection = db[cls.name]

        if new_values:
            try:
                _id = ObjectId(entry_id)
            except bson.errors.InvalidId:
                _id = entry_id

            try:
                result = collection.update_one({"_id": _id}, {"$set": new_values})
            except Exception as exc:
                return AppResult(False, exc)

            if result.modified_count != 1:
                return AppResult(False, "None of documents not modified")

        return AppResult(True)

    @classmethod
    def get_document(cls, _id: str) -> Optional[dict]:
        db = get_mongo_db()
        collection = db[cls.name]
        return collection.find_one(ObjectId(_id))

    @classmethod
    def del_document(cls, _id: str) -> AppResult:
        return _del_documents(cls.name, [ObjectId(_id)])

    @classmethod
    def exists_document_in_group(cls, key, value):
        db = get_mongo_db()
        collection = db[cls.name]
        return collection.count_documents({key: value}) > 1

    @classmethod
    def get_documents_by_filter(cls, filter_):
        db = get_mongo_db()
        collection = db[cls.name]
        return list(collection.find(filter_))


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


def _del_documents(collection_name: str, document_ids: List[str]) -> AppResult:
    db = get_mongo_db()
    collection = db[collection_name]

    try:
        deleted_count = collection.delete_many(
            {"_id": {"$in": document_ids}}
        ).deleted_count
    except Exception as exc:
        return AppResult(False, exc)

    return AppResult(deleted_count == len(document_ids))


def _add_document(collection_name: str, entry_data: Dict[str, Any]) -> AppResult:
    db = get_mongo_db()
    collection = db[collection_name]

    try:
        inserted_id = collection.insert_one(entry_data).inserted_id
    except Exception as exc:
        return AppResult(False, exc)

    return AppResult(True, data={"_id": str(inserted_id)})


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
        serverSelectionTimeoutMS=2000,
        connectTimeoutMS=15000,
    )
