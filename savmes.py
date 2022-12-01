import logging
from enum import Enum
from typing import Any, Dict
from dataclasses import dataclass, asdict
from datetime import datetime

from aiogram import Bot, types
from aiogram.filters import Command, callback_data
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db_utils as db
from common import AppResult


logger = logging.getLogger(__name__)


class MessageActions(int, Enum):
    DELETE = 0
    SAVE = 1
    DOWNLOAD_FILE = 2
    NOTE = 3

caption_by_action = {
    MessageActions.DELETE: "Delete",
    MessageActions.SAVE: "Save",
    MessageActions.DOWNLOAD_FILE: "Download",
    MessageActions.NOTE: "Note",
}

class SaveMessageData(callback_data.CallbackData, prefix="savmes_menu"):
    action: MessageActions
    message_id: str



@dataclass
class CB_MessageInfo:
    action: int = MessageActions.DELETE
    expire_at: int = 0


EXCLUDE_MESSAGE_FIELDS = {"chat": {"first_name", "last_name"}, "from_user": {"first_name", "last_name", "language_code"}}

DEFAULT_MESSAGE_TTL = 60*60*24*7


async def add_new_message(message_data: Dict[str, Any]) -> AppResult:
    expire_at = int(datetime.now().timestamp()) + DEFAULT_MESSAGE_TTL
    message_info = CB_MessageInfo(expire_at=expire_at)
    message_data["cb_message_info"] = asdict(message_info)

    logger.info("Adding message: {}".format(message_data))
    return db.NewMessagesCollection.add_document(message_data)


async def update_action_for_message(document_message_id: str, new_action: int):
    updated_data = asdict(CB_MessageInfo(action=action))
    if new_action == MessageActions.SAVE:
        updated_data.pop("expire_at", None)

    return db.NewMessagesCollection.update_document(document_message_id, updated_data)


async def process_saved_message():
    pass


async def download_file(file_id: str, bot: Bot) -> AppResult:
    file_ = await bot.get_file(file_id)
    file_path = file_.file_path

    base_file_name = file_path.split("/")[-1]
    unique_file_name = file_.file_unique_id
    dest_file_name = f"{base_file_name}_{unique_file_name}"

    try:
        await bot.download(file_id, destination=dest_file_name, timeout=60)
    except Exception as exc:
        return AppResult(False, exc)

    return AppResult(True)


def message_actions_menu_kb(message_id: str) -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()

    for action in MessageActions:
        kb_builder.button(
            text=caption_by_action[action], callback_data=SaveMessageData(action=action.value, message_id=message_id)
        )
    return kb_builder.as_markup()
