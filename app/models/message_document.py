from __future__ import annotations

from datetime import datetime
from typing import cast, Annotated, Any, Self, Sequence

from pydantic import ConfigDict, BeforeValidator, Field

from aiogram.types import Message

from app.actions import MessageActions

from .message_action import MessageAction
from .message_document_info import ActionsMenuUpdating, ActionsMenuStored, SVM_MsgdocInfo, PreparedMessageInfo



PyObjectId = Annotated[str, BeforeValidator(str)]

class MessageDocument(Message):
    id: PyObjectId | None = Field(default=None, alias="_id")
    is_subsequent_in_media_group: bool = Field(default=False)
    cb_message_info: SVM_MsgdocInfo | None = None

    model_config = ConfigDict(
        use_enum_values=True,
        extra="allow",
        validate_assignment=True,
        frozen=False,
        populate_by_name=True,
        arbitrary_types_allowed=True,
        defer_build=True,
        protected_namespaces=(),
    )

    @classmethod
    def from_message(cls, message: Message) -> Self:
        return cls(**message.model_dump(by_alias=True, exclude_unset=True, exclude_none=True))

    def get_current_action(self) -> MessageAction:
        if not self.cb_message_info:
            raise ValueError("Message info is not set")

        return self.cb_message_info.action

    def get_current_menu(self) -> ActionsMenuStored:
        if not self.cb_message_info:
            raise ValueError("Message info is not set")

        return self.cb_message_info.get_current_menu()

    def set_message_info(self, prepared_message_info: PreparedMessageInfo) -> None:
        self.cb_message_info = SVM_MsgdocInfo()

        self.update_message_info(
            new_actions_menu=prepared_message_info.actions_menu,
            new_action=prepared_message_info.action,
            new_ttl=prepared_message_info.ttl,
            entities=prepared_message_info.entities,
        )

    def update_message_info(
        self,
        actions_to_add: ActionsMenuUpdating | None = None,
        actions_to_del: Sequence[MessageAction | str] | None = None,
        new_actions_menu: ActionsMenuUpdating | None = None,
        new_action: MessageAction | None = MessageActions.NONE,
        new_perform_action_at: int | None = None,
        new_ttl: int | None = None,
        entities: list[dict[str, Any]] | None = None,
        reply_action_message_id: int | None = None,
    ) -> None:
        if self.cb_message_info is None:
            return

        self._update_menus(
            actions_to_add=actions_to_add,
            actions_to_del=actions_to_del,
            new_actions_menu=new_actions_menu,
        )

        msg_info = self.cb_message_info
        if new_ttl is not None:
            perform_action_at = int(datetime.now().timestamp()) + new_ttl
            msg_info.perform_action_at = perform_action_at
        elif new_perform_action_at is not None:
            msg_info.perform_action_at = new_perform_action_at

        if new_action is not None:
            msg_info.action = new_action
            if new_action.code == MessageActions.NONE.code:
                msg_info.perform_action_at = 0

        if entities is not None:
            msg_info.entities = entities

        if reply_action_message_id is not None:
            if reply_action_message_id == 0:
                msg_info.reply_action_message_id = None
            else:
                msg_info.reply_action_message_id = reply_action_message_id

    def _update_menus(
        self,
        actions_to_add: ActionsMenuUpdating | None,
        actions_to_del: Sequence[MessageAction | str] | None,
        new_actions_menu: ActionsMenuUpdating | None,
    ) -> None:

        if self.cb_message_info is None:
            return

        msg_info = self.cb_message_info
        actions_menus = msg_info.actions_menus or []
        current_menu = msg_info.actions_menus.pop() if msg_info.actions_menus else {}
        _old_menu_actions = set(current_menu)

        if actions_to_add is not None:
            for action, action_data in actions_to_add.items():
                action_code: str = (
                    action.code if isinstance(action, MessageAction) else action
                )
                current_menu[action_code] = action_data

        if actions_to_del is not None:
            for action_to_del in actions_to_del:
                action_to_del_code: str = (
                    cast(MessageAction, action_to_del).code
                    if isinstance(action_to_del, MessageAction) else action_to_del
                )
                current_menu.pop(action_to_del_code, None)

        if current_menu:
            actions_menus.append(current_menu)

        if new_actions_menu is not None:
            if new_actions_menu:
                actions_menus.append({
                    action.code: action_data
                    for action, action_data in new_actions_menu.items()
                })
            elif actions_menus:
                actions_menus.pop()

        try:
            actions_menus[-2].pop(MessageActions.BACK.code, None)
        except IndexError:
            ...

        if len(actions_menus) > 1:
            actions_menus[-1][MessageActions.BACK.code] = {}

        msg_info.actions_menus = actions_menus

    @property
    def message_text(self):
        return self.caption or self.text

    def get_from_chat_data(self) -> tuple[str, str]:

        if self.forward_from:
            return str(self.forward_from.id), (self.forward_from.username or self.forward_from.full_name)

        chat = self.forward_from_chat or self.chat
        return str(chat.id), (chat.title or chat.username or "unknown")

    def get_from_user_data(self) -> tuple[str | None, str | None]:
        if not self.from_user:
            return None, None
        return str(self.from_user.id), self.from_user.username
