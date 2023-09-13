from __future__ import annotations

import logging
from dacite import from_dict
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, Optional, Sequence, Tuple

import models
from aiogram.types import Message
from common import AppResult
from message_action import MessageAction
from models import MessagesBaseCollection, NewMessagesCollection, SavedMessagesCollection

from .actions import MessageActions
from .common import SVM_MsgdocInfo
from .constants import COMMON_GROUP_KEY

logger = logging.getLogger("cerrrbot")


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
            logger.warning(f"Empty message info: {exc}")
            cb_message_info = {}
        self.cb_message_info = from_dict(data_class=SVM_MsgdocInfo, data=cb_message_info)

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

        dict_obj = self.dict(
            exclude_none=True, exclude_defaults=True, exclude={"collection"}
        )
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
        delete_result = self.collection.del_document(self._id)
        if delete_result:
            self.collection = None
        return delete_result

    def dict(self, *args, **kwargs):
        dict_obj = super().dict(*args, **kwargs)
        dict_obj["cb_message_info"] = self._get_dumped_message_info()
        return dict_obj

    def update_message_info(
        self,
        new_action: Optional[MessageAction] = MessageActions.NONE,
        new_actions: Optional[Dict[str, Any]] = None,
        new_ttl: Optional[int] = None,
        entities: Optional[Dict[str, Any]] = None,
        reply_action_message_id: Optional[int] = None,
    ) -> AppResult:

        if new_ttl is not None:
            perform_action_at = int(datetime.now().timestamp()) + new_ttl
            self.cb_message_info.perform_action_at = perform_action_at

        if new_action is not None:
            self.cb_message_info.action = new_action.code
            if new_action == MessageActions.NONE:
                self.cb_message_info.perform_action_at = 0

        if new_actions is not None:
            if not self.cb_message_info.actions:
                self.cb_message_info.actions = new_actions
            else:
                self.cb_message_info.actions.update(new_actions)

        if entities is not None:
            self.cb_message_info.entities = entities

        if reply_action_message_id is not None:
            if reply_action_message_id == 0:
                self.cb_message_info.reply_action_message_id = None
            else:
                self.cb_message_info.reply_action_message_id = reply_action_message_id

        updated_message_info = self._get_dumped_message_info()
        return self.collection.update_document(
            self._id, {"cb_message_info": updated_message_info}
        )

    def _get_dumped_message_info(self):
        return asdict(self.cb_message_info)

    @property
    def message_text(self):
        return self.caption or self.text

    def get_from_chat_data(self) -> Tuple[str, str]:
        try:
            chat = self.forward_from_user
        except AttributeError:
            chat = self.forward_from_chat
        if not chat:
            chat = self.chat

        return str(chat.id), chat.title

    def get_from_user_data(self) -> Tuple[str, str]:
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
