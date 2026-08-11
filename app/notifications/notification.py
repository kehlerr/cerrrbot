from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app import app_settings

from typing import Any

class Notification(BaseModel):
    key: str = ""
    chat_id: int = 0
    text: str
    reply_to_message_id: int = 0
    send_at: int = 0
    send_count: int = 1
    repeat_in: int = 0

    @model_validator(mode="before")
    @classmethod
    def populate_dynamic_defaults(cls, data: dict[str, Any] | Any) -> dict[str, Any] | Any:
        if isinstance(data, dict):
            if "key" not in data:
                data["key"] = str(uuid4())
            if "chat_id" not in data:
                data["chat_id"] = app_settings.main_user_chat
        return data

    def need_repeat(self) -> bool:
        return self.repeat_in > 0 and self.send_count > 1

    def need_send(self) -> bool:
        now_tstamp = int(datetime.now(timezone.utc).timestamp())
        return self.send_count != 0 and now_tstamp >= self.send_at
