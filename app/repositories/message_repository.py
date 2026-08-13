from typing import Any

from bson.objectid import ObjectId

from app.infrastructure.repositories import MongoRepository
from app.models.message_document import MessageDocument


class MessageRepository(MongoRepository[MessageDocument]):
    model_class = MessageDocument

    async def get_messages_by_filter(self, query: dict[str, Any]) -> list[MessageDocument]:
        return await self.get_many(query)

    async def get_by_id(self, msgdoc_id: str) -> MessageDocument | None:
        return await self.get_one({"_id": ObjectId(msgdoc_id)})

    async def update_msgdoc(self, msgdoc: MessageDocument) -> int:
        return await self.update({"_id": ObjectId(msgdoc.id)}, msgdoc)

    async def delete_msgdoc(self, msgdoc: MessageDocument) -> int:
        return await self.delete({"_id": ObjectId(msgdoc.id)})

    async def delete_msgdocs(self, msgdocs: list[MessageDocument]) -> int | None:
        if not msgdocs:
            return None
        query = {"_id": {"$in": [ObjectId(msgdoc.id) for msgdoc in msgdocs]}}
        return await self.delete(query, multi=True)
