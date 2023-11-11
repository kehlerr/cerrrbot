import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import Message
from common import AppResult
from models import MessageDocument, NewMessagesCollection, SavedMessagesCollection

from .actions import MessageActions
from .constants import MESSAGE_DOCUMENT_TTL
from .content_strategies import (
    ContentStrategy,
    CustomizableContentStrategy,
    cls_strategy_by_content_type,
)

logger = logging.getLogger("cerrrbot")


def get_messages_to_perform_actions() -> list[MessageDocument]:
    filter_search = {
        "cb_message_info.perform_action_at": {
            "$lt": int(datetime.now().timestamp()),
            "$gt": 0,
        }
    }
    messages = NewMessagesCollection.get_documents_by_filter(filter_search)
    logger.debug("Found {} messages to perform action".format(len(messages)))
    return messages


def get_deprecated_messages() -> list[MessageDocument]:
    filter_search = {
        "date": {
            "$lte": datetime.utcnow() - timedelta(seconds=MESSAGE_DOCUMENT_TTL),
        }
    }
    messages = SavedMessagesCollection.get_documents_by_filter(filter_search)
    messages.extend(NewMessagesCollection.get_documents_by_filter(filter_search))
    logger.debug("Found {} deprecated messages".format(len(messages)))
    return messages


async def add_new_message(message: Message) -> AppResult:
    cls_strategy = _define_content_strategy(message)
    return await cls_strategy.add_new_message(message)


async def perform_message_action(
    message_id: str, bot: Bot, action_code: str | None = None
) -> AppResult:
    msgdoc = MessageDocument(message_id)
    if action_code:
        msgdoc.update_message_info(new_action=MessageActions.BY_CODE[action_code])

    action = msgdoc.cb_message_info.action
    cls_strategy = _define_content_strategy(msgdoc, action_code)
    return await cls_strategy.perform_action(action, msgdoc, bot)


def _define_content_strategy(
    msgdoc: Message | MessageDocument, action_code: str | None = None
) -> type[ContentStrategy]:
    if action_code and action_code in MessageActions.CUSTOM_ACTION_BY_CODE:
        return CustomizableContentStrategy
    return cls_strategy_by_content_type.get(msgdoc.content_type, ContentStrategy)
