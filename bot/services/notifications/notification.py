from datetime import datetime
from typing import Optional, Self

import orjson as json
from pydantic import BaseModel
from settings import ALLOWED_USERS


class Notification(BaseModel):
    text: str
    chat_id: Optional[str] = ALLOWED_USERS[0]
    reply_to_message_id: Optional[str] = None
    send_at: Optional[int] = 0
    send_count: Optional[int] = 1
    repeat_in: Optional[int] = 0

    def model_dump(self) -> str:
        return self.json()

    @staticmethod
    def model_load(cls, data: bytes) -> Self:
        data = json.loads(data.decode())
        return cls(**data)

    def need_repeat(self) -> bool:
        return self.repeat_in > 0 and self.send_count > 1

    def need_send(self) -> bool:
        now_tstamp = int(datetime.utcnow().timestamp())
        return self.send_count > 0 and now_tstamp >= self.send_at
