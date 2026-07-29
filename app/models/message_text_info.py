from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict

from .message_source import UserInfo


class MessageEntity(BaseModel):
    type: str
    offset: int
    length: int
    url: str | None = None
    user: UserInfo | None = None
    language: str | None = None
    custom_emoji_id: str | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class MessageTextInfo(BaseModel):
    text: str | None = None
    caption: str | None = None
    entities: list[MessageEntity] | None = None
    caption_entities: list[MessageEntity] | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @classmethod
    def from_message(cls, message: Any) -> Self | None:
        raw_dump = message.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
        text_info = cls.model_validate(raw_dump)
        if not text_info.model_dump(exclude_none=True, exclude_unset=True):
            return None
        return text_info

    @property
    def message_text(self) -> str | None:
        return self.caption or self.text
