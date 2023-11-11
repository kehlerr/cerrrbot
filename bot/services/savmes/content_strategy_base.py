import logging
from typing import Any

from aiogram.types import Message

from common import AppResult
from models import (
    ActionsData,
    COMMON_GROUP_KEY,
    MessageDocument,
    NewMessagesCollection,
    SVM_MsgdocInfo,
    SVM_PreparedMessageInfo,
    SVM_ReplyInfo,
)
from settings import TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION

from .actions import MessageActions
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
        add_result = NewMessagesCollection.add_document(message_data)
        if add_result:
            added_message_id = add_result.data["_id"]
            logger.info("Saved new message with _id:[{}]".format(str(added_message_id)))
            message_info = cls._prepare_message_info(message_data)
            msgdoc = MessageDocument(added_message_id)
            msgdoc.update_message_info(
                new_actions_menu=message_info.actions,
                new_action=message_info.action,
                new_ttl=message_info.ttl,
                entities=message_info.entities,
            )
            cls._prepare_reply_info(msgdoc.cb_message_info, add_result.data)
        else:
            logger.error(
                "Error occured while adding received message: {}".format(add_result)
            )
        return add_result

    @classmethod
    def _prepare_message_info(
        cls, message_data: dict[str, Any]
    ) -> SVM_PreparedMessageInfo:
        actions = None
        common_group_id = message_data.get(COMMON_GROUP_KEY)
        if not common_group_id or not NewMessagesCollection.exists_document_in_group(
            COMMON_GROUP_KEY, common_group_id
        ):
            actions = {action.code: {} for action in cls.POSSIBLE_ACTIONS}
        parsed_actions = cls._parse_custom_actions(message_data)
        if parsed_actions:
            if actions is None:
                actions = {}
            actions.update(parsed_actions)

        return SVM_PreparedMessageInfo(
            action=cls.DEFAULT_ACTION,
            actions=actions,
            ttl=cls.DEFAULT_MESSAGE_TTL,
            entities=None,
        )

    @classmethod
    def _parse_custom_actions(cls, message_data: dict[str, Any]) -> ActionsData | None:
        message_text = message_data.get("caption") or message_data.get("text")
        if not message_text:
            return None
        parser = MessageParser(message_text)
        parser.parse()
        return parser.actions

    @classmethod
    def _prepare_reply_info(
        cls, msgdoc_info: SVM_MsgdocInfo, result_data: dict[str, Any]
    ) -> None:
        force_need_update_buttons = result_data.get("need_update_buttons")
        need_update_buttons = False
        reply_actions = []
        for action_code, action_data in msgdoc_info.get_current_menu().items():
            action = MessageActions.BY_CODE[action_code]
            additional_caption = action_data.get("additional_caption", "")
            if additional_caption:
                action = action.copy(
                    update={"caption": f"{action.caption}{additional_caption}"}, deep=True
                )
                if force_need_update_buttons is None:
                    need_update_buttons = True
            reply_actions.append(action)
        if force_need_update_buttons is not None:
            need_update_buttons = force_need_update_buttons
        else:
            need_update_buttons = need_update_buttons or msgdoc_info.actions_updated
        result_data["reply_info"] = SVM_ReplyInfo(
            actions=sorted(reply_actions),
            reply_action_message_id=msgdoc_info.reply_action_message_id,
            need_update_buttons=need_update_buttons,
            popup_text=result_data.pop("popup_text", None),
        )
