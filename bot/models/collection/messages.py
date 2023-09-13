from typing import Any

from common import AppResult
from .base import CollectionModel


class NewMessagesCollection(CollectionModel):
    name = "new_messages"


class SavedMessagesCollection(CollectionModel):
    name = "saved_messages"

    @classmethod
    def add_document(cls, entry_data: dict[str, Any]) -> AppResult:
        if not entry_data.get("_id"):
            return AppResult(
                False, "Invalid new entry_data, missed _id field:{}".format(entry_data)
            )

        return super().add_document(entry_data)
