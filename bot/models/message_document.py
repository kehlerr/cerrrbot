from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional, Sequence

import models
from aiogram.types import Message
from common import AppResult
from models import (
    MessagesBaseCollection,
    NewMessagesCollection,
    SavedMessagesCollection,
)

from .message_action import MESSAGE_ACTION_BACK, MESSAGE_ACTION_NONE, MessageAction
from .message_document_info import SVM_MsgdocInfo, ActionsMenuUpdating

logger = logging.getLogger("cerrrbot")


COMMON_GROUP_KEY: str = "media_group_id"


class MessageDocument(Message):
    _id: str

    def __init__(self, document_id: str):
        self.__config__.allow_mutation = True
        document_data = self._fetch_document_data(document_id)
        super().__init__(**document_data)
        self._load()

    def _load(self) -> None:
        try:
            cb_message_info = self.cb_message_info
        except AttributeError as exc:
            logger.debug(f"Empty message info: {exc}")
            cb_message_info = {}
        self.cb_message_info = SVM_MsgdocInfo(**cb_message_info)

    def add_to_collection(
        self, collection: Optional[MessagesBaseCollection] = SavedMessagesCollection
    ) -> AppResult:
        if self.collection == collection:
            return AppResult(
                False,
                "Message with id: {} already in collection {}".format(
                    self._id, self.collection
                ),
            )

        dict_obj = self.json_dict()
        add_result = collection.add_document(dict_obj)
        if add_result:
            self.collection = collection
        return add_result

    def get_msgdocs_by_group(self) -> Optional[Sequence[MessageDocument]]:
        try:
            group_key_value = getattr(self, COMMON_GROUP_KEY)
            if group_key_value is None:
                raise TypeError
            filter_search = {COMMON_GROUP_KEY: group_key_value}
        except (AttributeError, TypeError):
            return None

        return (
            MessageDocument(md["_id"])
            for md in NewMessagesCollection.get_documents_by_filter(filter_search)
        )

    def delete(self) -> AppResult:
        logger.info(f"delete document: id:{self._id}, collection: {self.collection}")
        delete_result = self.collection.del_document(self._id)
        if delete_result:
            self.collection = None
        return delete_result

    def menu_go_back(self) -> None:
        self.update_message_info(new_action=MESSAGE_ACTION_NONE, new_actions_menu={})

    def json_dict(self) -> dict[str, Any]:
        return self.dict(exclude_none=True, exclude_defaults=True, exclude={"collection"})

    def dict(self, *args, **kwargs):
        dict_obj = super().dict(*args, **kwargs)
        dict_obj["cb_message_info"] = self._get_dumped_message_info()
        return dict_obj

    def update_message_info(
        self,
        actions_to_add: ActionsMenuUpdating | None = None,
        actions_to_del: Sequence[MessageAction, str] | None = None,
        new_actions_menu: ActionsMenuUpdating | None = None,
        new_action: MessageAction | None = MESSAGE_ACTION_NONE,
        new_ttl: int | None = None,
        entities: dict[str, Any] | None = None,
        reply_action_message_id: int | None = None,
    ) -> AppResult:
        self._update_menus(
            actions_to_add=actions_to_add,
            actions_to_del=actions_to_del,
            new_actions_menu=new_actions_menu,
        )

        msg_info = self.cb_message_info
        if new_ttl is not None:
            perform_action_at = int(datetime.now().timestamp()) + new_ttl
            msg_info.perform_action_at = perform_action_at

        if new_action is not None:
            msg_info.action = new_action.code
            if new_action.code == MESSAGE_ACTION_NONE.code:
                msg_info.perform_action_at = 0

        if entities is not None:
            msg_info.entities = entities

        if reply_action_message_id is not None:
            if reply_action_message_id == 0:
                msg_info.reply_action_message_id = None
            else:
                msg_info.reply_action_message_id = reply_action_message_id

        updated_message_info = self._get_dumped_message_info()
        return self.collection.update_document(
            self._id, {"cb_message_info": updated_message_info}
        )

    def _update_menus(
        self,
        actions_to_add: ActionsMenuUpdating | None,
        actions_to_del: Sequence[MessageAction, str] | None,
        new_actions_menu: ActionsMenuUpdating | None,
    ) -> None:
        msg_info = self.cb_message_info
        actions_menus = msg_info.actions_menus
        current_menu = actions_menus.pop() if actions_menus else {}
        _old_menu_actions = set(list(current_menu.keys()))

        if actions_to_add is not None:
            for action, action_data in actions_to_add.items():
                action_code: str = (
                    action.code if isinstance(action, MessageAction) else action
                )
                current_menu[action_code] = action_data

        if actions_to_del is not None:
            for action in actions_to_del:
                action_code: str = (
                    action.code if isinstance(action, MessageAction) else action
                )
                current_menu.pop(action_code, None)

        if current_menu:
            actions_menus.append(current_menu)

        if new_actions_menu is not None:
            if new_actions_menu:
                for action in list(new_actions_menu.keys()):
                    action_code: str = (
                        action.code if isinstance(action, MessageAction) else action
                    )
                    new_actions_menu[action_code] = new_actions_menu.pop(action)
                actions_menus.append(new_actions_menu)
            elif actions_menus:
                msg_info.actions_menus.pop()

        try:
            msg_info.actions_menus[-2].pop(MESSAGE_ACTION_BACK.code, None)
        except IndexError:
            ...

        if len(msg_info.actions_menus) > 1:
            msg_info.actions_menus[-1][MESSAGE_ACTION_BACK.code] = {}

        _new_menu_actions = set(list(msg_info.get_current_menu().keys()))
        msg_info.actions_updated = _new_menu_actions != _old_menu_actions

    def _get_dumped_message_info(self) -> dict:
        return self.cb_message_info.dict()

    @property
    def message_text(self):
        return self.caption or self.text

    def get_from_chat_data(self) -> tuple[str, str]:
        try:
            chat = self.forward_from_user
        except AttributeError:
            chat = self.forward_from_chat
        if not chat:
            chat = self.chat

        return str(chat.id), chat.title

    def get_from_user_data(self) -> tuple[str, str]:
        return self.from_user.id, self.from_user.username

    def _fetch_document_data(self, document_id):
        for collection in models.collections:
            message_data = collection.get_document(document_id)
            if message_data:
                message_data["_id"] = document_id
                message_data["collection"] = collection
                return message_data

        raise Exception("Message not found")

    @staticmethod
    def set_reply_action_message_id(
        document_message_id: str, action_message_id
    ) -> AppResult:
        db_key = "cb_message_info.reply_action_message_id"
        return NewMessagesCollection.update_document(
            document_message_id, {db_key: action_message_id}
        )
