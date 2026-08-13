from typing import Any, cast

from loguru import logger
from pydantic import BaseModel
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError

from app.types import PydanticModelClass

from .exceptions import InsertEntryError, UpdateEntryError


class MongoRepository[TPydanticModel]:
    collection_name: str
    model_class: type[TPydanticModel]

    def __init__(
        self, db: AsyncDatabase, collection_name: str | None = None, model_class: type[TPydanticModel] | None = None
    ) -> None:
        self._db = db

        if collection_name:
            self.collection_name = collection_name
        self.collection: AsyncCollection = self._db[self.collection_name]

        if model_class:
            self.model_class = model_class

        self._model_class = cast(PydanticModelClass[TPydanticModel], model_class or self.model_class)

    async def get_one(self, query: dict[str, Any]) -> TPydanticModel | None:
        if document := await self.collection.find_one(query):
            return self._model_class.model_validate(document)
        return None

    async def get_many(self, query: dict[str, Any], limit: int = 0, skip: int = 0) -> list[TPydanticModel]:
        cursor = self.collection.find(query).skip(skip).limit(limit)
        documents = await cursor.to_list(length=None if limit == 0 else limit)
        return [self._model_class.model_validate(doc) for doc in documents]

    async def insert(self, item: TPydanticModel) -> TPydanticModel:
        document = cast(PydanticModelClass[TPydanticModel], item).model_dump(
            by_alias=True, exclude_unset=True, exclude_none=True
        )

        try:
            await self.collection.insert_one(document)
        except PyMongoError as exc:
            logger.exception("Error occured while inserting document")
            raise InsertEntryError(document=document) from exc
        else:
            logger.debug(f"Successfully inserted document: {document}")

        return self._model_class.model_validate(document)

    async def update(self, query: dict[str, Any], update_data: dict[str, Any] | TPydanticModel, multi: bool = False) -> int:
        if isinstance(update_data, BaseModel):
            payload_data = update_data.model_dump(by_alias=True, exclude_unset=True)
            payload_data.pop("_id", None)

            update_payload = {"$set": payload_data}
        else:
            update_payload = cast(dict[str, Any], update_data)

        try:
            if multi:
                result = await self.collection.update_many(query, update_payload)
            else:
                result = await self.collection.update_one(query, update_payload)
        except PyMongoError as exc:
            logger.exception("Error occured while updating document")
            raise UpdateEntryError(query=query, update_payload=update_payload) from exc
        else:
            logger.debug(f"Document updated successfully: {update_payload}")

        return result.modified_count

    async def delete(self, query: dict[str, Any], multi: bool = False) -> int:
        if multi:
            result = await self.collection.delete_many(query)
        else:
            result = await self.collection.delete_one(query)

        return result.deleted_count

    async def clear_collection(self) -> int:
        result = await self.collection.delete_many({})
        return result.deleted_count

    async def drop_collection(self) -> None:
        await self.collection.drop()

    async def count(self, query: dict[str, Any] | None = None) -> int:
        return await self.collection.count_documents(query or {})
