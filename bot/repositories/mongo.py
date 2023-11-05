import logging
from typing import Any, Iterable, Optional

import bson
import pymongo
from bson.objectid import ObjectId
from common import AppResult
from pymongo.errors import ServerSelectionTimeoutError
from settings import MONGO_DB_HOST, MONGO_DB_NAME, MONGO_DB_PORT

logger = logging.getLogger("cerrrbot")


def init(collections: Iterable):
    logger.info("Starting init DB...")
    db = get_mongo_db()
    existing_collections = db.list_collection_names()
    if existing_collections:
        logger.info(
            "DB already initialized with next collections:{}".format(existing_collections)
        )
        return

    for collection_config in collections:
        db.create_collection(collection_config.name)


def select(collection_name: str, entry_id: Optional[str] = None, filter_: Optional[dict] = None) -> list:
    db = get_mongo_db()
    collection = db[collection_name]

    documents = []
    if entry_id is not None:
        document = collection.find_one(_document_id(entry_id))
        if document:
            documents.append(document)

    if filter_ is not None:
        documents_filter = list(collection.find(filter_))
        if documents_filter:
            documents.extend(documents_filter)

    return documents


def insert(collection_name: str, entry_data: dict[str, Any]) -> AppResult:
    db = get_mongo_db()
    collection = db[collection_name]

    entry_data["_id"] = _document_id(entry_data.get("_id"))

    try:
        inserted_id = collection.insert_one(entry_data).inserted_id
    except Exception as exc:
        return AppResult(False, exc)

    return AppResult(True, data={"_id": str(inserted_id)})


def update(collection_name: str, entry_id: str, new_values: dict[str, Any]) -> AppResult:
    if not new_values:
        return AppResult()

    db = get_mongo_db()
    collection = db[collection_name]

    try:
        result = collection.update_one({"_id": _document_id(entry_id)}, {"$set": new_values})
    except Exception as exc:
        return AppResult(False, exc)

    if result.modified_count != 1:
        return AppResult(False, "None of documents not modified")

    return AppResult(True)


def delete_many(collection_name: str, entities_ids: list[str]) -> AppResult:
    db = get_mongo_db()
    collection = db[collection_name]

    documents_ids = [_document_id(_id) for _id in entities_ids]

    try:
        deleted_count = collection.delete_many(
            {"_id": {"$in": documents_ids}}
        ).deleted_count
    except Exception as exc:
        return AppResult(False, exc)

    return AppResult(deleted_count == len(entities_ids))


def count(collection_name: str, filter_: dict[str, Any] | None = None) -> int:
    db = get_mongo_db()
    collection = db[collection_name]
    if filter_:
        return collection.count_documents(filter_)
    else:
        return collection.count_documents()


def _document_id(entry_id: Any) -> ObjectId:
    try:
        _id = ObjectId(entry_id)
    except bson.errors.InvalidId:
        _id = entry_id

    return _id


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
