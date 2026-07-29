
from dataclasses import dataclass
from datetime import datetime
import hashlib
from typing import Any, Self

from aiogram.enums import MessageOriginType
from pydantic import BaseModel, ConfigDict, Field



class UserInfo(BaseModel):
    id: int = 0
    is_bot: bool = False
    first_name: str = ""
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name or ''}".strip()


class ChatInfo(BaseModel):
    id: int = 0
    type: str = "private"
    title: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class MessageForwardOrigin(BaseModel):
    type: MessageOriginType
    date: datetime
    sender_user: UserInfo | None = None
    sender_user_name: str | None = None
    sender_chat: ChatInfo | None = None
    chat: ChatInfo | None = None
    message_id: int | None = None
    author_signature: str | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def get_message_source_data(self, message_chat: ChatInfo) -> MessageSourceData | None:
        origin_type = self.type

        if origin_type == MessageOriginType.USER and (user := self.sender_user):
            return MessageSourceData(chat_id=message_chat.id, user_id=user.id, title=user.full_name, tag=user.username)
        elif origin_type == MessageOriginType.HIDDEN_USER and (name := self.sender_user_name):
            encoded_name = hashlib.sha256(name.encode()).hexdigest()[:8]
            return MessageSourceData(chat_id=message_chat.id, title=encoded_name)
        elif origin_type == MessageOriginType.CHAT and (chat := self.sender_chat):
            return MessageSourceData(chat_id=chat.id, title=chat.title or "unknown", tag=chat.username)
        elif origin_type in (MessageOriginType.CHANNEL, "channel") and (chat := self.chat):
                return MessageSourceData(chat_id=chat.id, title=chat.title or "unknown", tag=chat.username)

        return None


class MessageSourceInfo(BaseModel):
    chat: ChatInfo = Field(default_factory=lambda: ChatInfo(id=0, type="private"))
    from_user: UserInfo | None = None
    forward_origin: MessageForwardOrigin | None = None
    forward_from: UserInfo | None = None
    forward_from_chat: ChatInfo | None = None
    forward_date: datetime | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @classmethod
    def from_message(cls, message: Any) -> Self:
        raw_dump = message.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
        return cls.model_validate(raw_dump)


@dataclass(frozen=True)
class MessageSourceData:
    chat_id: int
    user_id: int | None = None
    title: str = "unknown"
    tag: str | None = None

    @property
    def source_id(self) -> str:
        if self.user_id:
            return f"{self.chat_id}_{self.user_id}"
        return str(self.chat_id)
