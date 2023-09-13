from typing import Optional, Self

import orjson as json
from pydantic import BaseModel

from settings import ALLOWED_USERS


class Notification(BaseModel):
    text: str
    chat_id: Optional[str] = ALLOWED_USERS[0]
    reply_to_message_id: Optional[str] = None

    def model_dump(self) -> str:
        return self.json()

    @staticmethod
    def model_load(cls, data: bytes) -> Self:
        data = json.loads(data.decode())
        return cls(**data)
