import logging
from dataclasses import replace
from typing import Any, Dict, List, Optional

import db_utils as db
from aiogram.types import Message
from common import AppResult
from message_action import MessageAction
from settings import TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION

from .actions import MessageActions
from .common import SVM_MsgdocInfo, SVM_ReplyInfo
from .constants import COMMON_GROUP_KEY
from .message_document import MessageDocument
from .message_parser import MessageParser

logger = logging.getLogger("cerrrbot")


class ContentStrategyBase:
    DEFAULT_MESSAGE_TTL = TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION
    DEFAULT_ACTION = MessageActions.DELETE_1

    POSSIBLE_ACTIONS = {
        MessageActions.KEEP,
        MessageActions.DELETE_REQUEST,
    }

    @classmethod
    async def add_new_message(cls, message: Message) -> AppResult:
        message_data = message.dict(exclude_none=True, exclude_defaults=True)
        logger.info("Adding message: {}".format(message_data))
        add_result = db.NewMessagesCollection.add_document(message_data)
        if add_result:
            added_message_id = add_result.data["_id"]
            logger.info("Saved new message with _id:[{}]".format(str(added_message_id)))
            message_info = cls._prepare_message_info(message_data)
            MessageDocument(added_message_id).update_message_info(
                message_info.action,
                message_info.actions,
                cls.DEFAULT_MESSAGE_TTL,
                message_info.entities,
            )
            cls._prepare_reply_info(message_info, add_result.data)
        else:
            logger.error(
                "Error occured while adding received message: {}".format(add_result)
            )
        return add_result

    @classmethod
    def _prepare_message_info(cls, message_data: Dict[str, Any]) -> SVM_MsgdocInfo:
        message_info = SVM_MsgdocInfo(action=cls.DEFAULT_ACTION)
        common_group_id = message_data.get(COMMON_GROUP_KEY)
        if not common_group_id or not db.NewMessagesCollection.exists_document_in_group(
            COMMON_GROUP_KEY, common_group_id
        ):
            message_info.actions = {action.code: {} for action in cls.POSSIBLE_ACTIONS}
        cls._parse_message(message_data, message_info)
        return message_info

    @classmethod
    def _prepare_reply_info(
        cls, message_info: SVM_MsgdocInfo, result_data: Dict[str, Any]
    ) -> None:
        try:
            reply_info = result_data["reply_info"]
        except KeyError:
            reply_info = SVM_ReplyInfo(**vars(message_info))

        if not reply_info.actions:
            return

        reply_actions = []
        for action_code, action_data in reply_info.actions.items():
            action = MessageActions.BY_CODE[action_code]
            additional_caption = action_data.get("additional_caption")
            if additional_caption:
                action = replace(action, caption=f"{action.caption}{additional_caption}")
            reply_actions.append(action)
        reply_info.actions = sorted(reply_actions)

        result_data["reply_info"] = reply_info

    @classmethod
    def _parse_message(
        cls, message_data: Dict[str, Any], message_info: SVM_MsgdocInfo
    ) -> None:
        message_text = message_data.get("caption") or message_data.get("text")
        if not message_text:
            return
        parser = MessageParser(message_text, message_info)
        parser.parse()
        message_info.actions.update(parser.actions)

    @classmethod
    def _update_actions(
        cls,
        msgdoc: MessageDocument,
        to_delete: Optional[List[MessageAction]] = None,
        to_add: Optional[Dict[MessageAction, Any]] = None,
    ) -> AppResult:
        message_actions = msgdoc.cb_message_info.actions
        if to_delete:
            for action in to_delete:
                message_actions.pop(action.code, None)

        if to_add:
            for action, data in to_add.items():
                message_actions[action.code] = data or {}
        result = msgdoc.update_message_info(new_actions=message_actions)
        return result
