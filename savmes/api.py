import logging
import os
import sys
from datetime import datetime
from typing import Optional

from aiogram import Bot
from aiogram.types import Message

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import db_utils as db
from common import AppResult

from .common import MessageActions
from .content_strategies import ContentStrategy, cls_strategy_by_content_type
from .message_document import MessageDocument

logger = logging.getLogger("cerrrbot")


async def check_actions_on_new_messages(bot: Bot):
    filter_search = {
        "cb_message_info.perform_action_at": {
            "$lt": int(datetime.now().timestamp()),
            "$gt": 0,
        }
    }
    messages = db.NewMessagesCollection.get_documents_by_filter(filter_search)
    result = AppResult()
    for message_data in messages:
        # MessageDocument(message_data["_id"]).delete()
        # continue
        result_ = await perform_message_action(message_data["_id"], bot)
        result.merge(result_)

    return result


async def add_new_message(message: Message) -> AppResult:
    cls_strategy = cls_strategy_by_content_type.get(message.content_type, ContentStrategy)
    result = await cls_strategy.add_new_message(message)
    return result


async def perform_message_action(
    message_id: str, bot: Bot, action_code: Optional[str] = None
) -> AppResult:
    msgdoc = MessageDocument(message_id)
    if action_code:
        msgdoc.update_message_info(MessageActions.ACTION_BY_CODE[action_code])

    action = msgdoc.cb_message_info.action
    cls_strategy = cls_strategy_by_content_type.get(msgdoc.content_type, ContentStrategy)
    result = await cls_strategy.perform_action(action, msgdoc, bot)
    logger.info("[{}]Result performed action {}:{}".format(msgdoc, action, result))
    return result
