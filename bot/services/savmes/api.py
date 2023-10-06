import logging
from datetime import datetime, timedelta
from typing import Optional, List

from aiogram import Bot
from aiogram.types import Message

from common import AppResult
from models import NewMessagesCollection, SavedMessagesCollection

from .actions import MessageActions
from .constants import MESSAGE_DOCUMENT_TTL
from .content_strategies import ContentStrategy, cls_strategy_by_content_type
from .message_document import MessageDocument

logger = logging.getLogger("cerrrbot")


def get_messages_to_perform_actions() -> List[MessageDocument]:
    filter_search = {
        "cb_message_info.perform_action_at": {
            "$lt": int(datetime.now().timestamp()),
            "$gt": 0,
        }
    }
    messages = NewMessagesCollection.get_documents_by_filter(filter_search)
    logger.debug("Found {} messages to perform action".format(len(messages)))
    return messages


def get_deprecated_messages() -> List[MessageDocument]:
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
    cls_strategy = cls_strategy_by_content_type.get(message.content_type, ContentStrategy)
    return await cls_strategy.add_new_message(message)


async def perform_message_action(
    message_id: str, bot: Bot, action_code: Optional[str] = None
) -> AppResult:
    msgdoc = MessageDocument(message_id)
    if action_code:
        msgdoc.update_message_info(MessageActions.BY_CODE[action_code])

    action = msgdoc.cb_message_info.action
    cls_strategy = cls_strategy_by_content_type.get(msgdoc.content_type, ContentStrategy)
    return await cls_strategy.perform_action(action, msgdoc, bot)
