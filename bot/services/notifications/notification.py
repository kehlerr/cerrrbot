from datetime import datetime
from typing import Optional, Self

import orjson as json
from pydantic import BaseModel
from settings import ALLOWED_USERS


class Notification(BaseModel):
    text: str
    chat_id: str = ALLOWED_USERS[0]
    reply_to_message_id: int = 0
    send_at: int = 0
    send_count: int = 1
    repeat_in: int = 0

    def need_repeat(self) -> bool:
        return self.repeat_in > 0 and self.send_count > 1

    def need_send(self) -> bool:
        now_tstamp = int(datetime.utcnow().timestamp())
        return self.send_count > 0 and now_tstamp >= self.send_at
