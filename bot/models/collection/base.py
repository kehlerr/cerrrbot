from typing import Any, Optional

from common import AppResult
from repositories import db


class CollectionModel:
    name: str
    ttl: Optional[int] = 0

    @classmethod
    def add_document(cls, entry_data: dict[str, Any]) -> AppResult:
        return db.insert(cls.name, entry_data)

    @classmethod
    def update_document(cls, entry_id: str, new_values: dict[str, Any]) -> AppResult:
        return db.update(cls.name, entry_id, new_values)

    @classmethod
    def get_document(cls, entry_id: str) -> Optional[dict]:
        result = db.select(cls.name, entry_id)
        return result[0] if result else None

    @classmethod
    def del_document(cls, _id: str) -> AppResult:
        return db.delete_many(cls.name, [_id])

    @classmethod
    def exists_document_in_group(cls, key, value) -> bool:
        return db.count(cls.name, filter_={key: value}) > 1

    @classmethod
    def get_documents_by_filter(cls, filter_) -> list:
        return db.select(cls.name, filter_=filter_)

