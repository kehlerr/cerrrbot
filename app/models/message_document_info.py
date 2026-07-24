import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.actions import MessageActions
from app.models import MessageAction

logger = logging.getLogger("cerrrbot")


ActionsData = dict[str, Any]
ActionsMenuStored = dict[str, ActionsData]
ActionsMenuUpdating = dict[MessageAction, ActionsData]


class SVM_MsgdocInfo(BaseModel):
    action: MessageAction = MessageActions.NONE
    perform_action_at: int = Field(default=0)
    reply_action_message_id: int | None = Field(default=None)
    entities: list[dict[str, Any]] | None = Field(default=None)
    actions_menus: list[ActionsMenuStored] | None = Field(default=None)

    @field_validator("action", mode="before")
    @classmethod
    def convert_action(cls, action_value: Any) -> MessageAction:
        if isinstance(action_value, str):
            return MessageActions.BY_CODE.get(action_value, MessageActions.NONE)
        return action_value

    def get_current_menu(self) -> ActionsMenuStored:
        return self.actions_menus[-1] if self.actions_menus else {}


class PreparedMessageInfo(BaseModel):
    action: MessageAction
    actions_menu: ActionsMenuUpdating
    ttl: int
    entities: list[dict[str, Any]] | None = Field(default=None)


class SVM_ReplyInfo(BaseModel):
    result_info_text: str | None = Field(default=None)
    need_update_buttons: bool = Field(default=False)
    actions: list[MessageAction] = Field(default_factory=lambda: [])
    reply_action_message_id: int | None = Field(default=None)
