import logging
from typing import Any, Optional

from pydantic import BaseModel, Field, validator

from .message_action import MESSAGE_ACTION_NONE, MessageAction

logger = logging.getLogger("cerrrbot")


class SVM_MsgdocInfo(BaseModel):
    action: str | MessageAction = MESSAGE_ACTION_NONE
    perform_action_at: int = 0
    reply_action_message_id: Optional[int] = 0
    entities: Optional[list[dict[str, Any]]] = None
    actions: dict[str, Any] = Field(default_factory=lambda: {})


class SVM_ReplyInfo(SVM_MsgdocInfo):
    popup_text: str | None = None
    need_edit_buttons: Optional[bool] = True
    actions: tuple[MessageAction, ...] | dict[str, Any] = Field(default_factory=lambda: {})

    @validator("actions")
    def prepare_actions(cls, v: dict | tuple[MessageAction, ...], **kwargs) -> dict[str, Any]:
        if not isinstance(v, dict):
            return {a.code: {} for a in v}
        return v