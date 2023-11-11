import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from .message_action import MESSAGE_ACTION_NONE, MessageAction

logger = logging.getLogger("cerrrbot")


ActionsData = dict[str, Any]
ActionsMenuStored = dict[str, ActionsData]
ActionsMenuUpdating = dict[MessageAction, ActionsData]


class SVM_MsgdocInfo(BaseModel):
    action: str | MessageAction = MESSAGE_ACTION_NONE
    perform_action_at: int = 0
    reply_action_message_id: int = 0
    entities: Optional[list[dict[str, Any]]] = None
    actions_menus: list[ActionsMenuStored] = Field(default_factory=list)
    actions_updated: bool = False

    def get_current_menu(self) -> ActionsMenuStored:
        try:
            return self.actions_menus[-1]
        except IndexError:
            return {}


class SVM_PreparedMessageInfo(BaseModel):
    action: MessageAction
    actions: dict[str, dict[str, Any]] | None
    ttl: int
    entities: list[dict[str, Any]] | None


class SVM_ReplyInfo(BaseModel):
    popup_text: str | None = None
    need_update_buttons: bool = False
    actions: list[MessageAction] = Field(default_factory=lambda: [])
    reply_action_message_id: int = 0
