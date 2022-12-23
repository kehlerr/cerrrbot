import logging
from enum import Enum
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime

from aiogram import Bot
from aiogram.types import ContentType, Message

import db_utils as db
from common import AppResult


logger = logging.getLogger(__name__)
logger = logging.getLogger("__main__")


class MessageActions(str, Enum):
    DELETE = "Delete"
    SAVE = "Save"
    DOWNLOAD_FILE = "Download"
    DOWNLOAD_ALL = "Download all"
    DOWNLOAD_DELAY = "Download delay"
    NOTE = "Note"
    TODO = "Note ToDo"
    BOOKMARK = "Add bookmark"


@dataclass
class CB_MessageInfo:
    action: str = MessageActions.DELETE
    perform_action_at: int = 0
    common_group_key: Optional[str] = None
    content_type: ContentType = ContentType.TEXT


COMMON_GROUP_KEYS = {"media_group_id",}


async def update_action_for_message(document_message_id: str, new_action: int):
    updated_data = asdict(CB_MessageInfo(action=new_action))
    if new_action == MessageActions.SAVE:
        updated_data.pop("expire_at", None)

    return db.NewMessagesCollection.update_document(document_message_id, {"cb_message_info": updated_data})


async def set_action_message_id(document_message_id: str, action_message_id):
    return db.NewMessagesCollection.update_document(document_message_id, {"action_message_id": action_message_id})


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


class ContentStrategy:
    DEFAULT_MESSAGE_TTL = 30*60
    DEFAULT_ACTION = MessageActions.DELETE

    @classmethod
    async def perform_action(cls, action: str, message_id: str, bot: Bot) -> AppResult:
        print("ACTION_IS:",action)
        action_method = cls._get_action_by_code(action)
        result = await action_method(message_id, bot)
        return result

    @classmethod
    def _get_action_by_code(cls, code: MessageActions) -> Optional[Callable]:
        if code == MessageActions.SAVE:
            return cls.save
        elif code == MessageActions.DELETE:
            return cls.delete

        return None

    @classmethod
    async def save(self, message_id) -> AppResult:
        message_data = db.NewMessagesCollection.get_document(message_id)
        if not message_data:
            return AppResult(False, "Message with id: {} not found".format(message_id))

        add_result = db.SavedMessagesCollection.add_document(message_data)
        del_result = db.NewMessagesCollection.del_document(message_id)
        common_result = add_result.merge(del_result)
        return common_result

    @classmethod
    async def delete(self, message_id: str, bot: Bot) -> AppResult:
        message_data = db.NewMessagesCollection.get_document(message_id)
        if not message_data:
            return AppResult(False, "[{}] Message not found".format(message_id))

        chat_id = message_data["chat"]["id"]
        try:
            await bot.delete_message(chat_id, message_data["action_message_id"])
        except KeyError:
            logger.info("[{}] Not found action message, no need to delete it".format(message_id))
        except Exception as exc:
            logger.error(exc)
            return AppResult(False, str(exc))

        try:
            result = await bot.delete_message(chat_id, message_data["message_id"])
        except Exception as exc:
            logger.error(exc)
            return AppResult(False, str(exc))

        if not result:
            return AppResult(result)

        result = db.NewMessagesCollection.del_document(message_id)

        return AppResult(result)

    @classmethod
    async def add_new_message(cls, message_data: Dict[str, Any], content_type: ContentType) -> AppResult:
        perform_action_at = int(datetime.now().timestamp()) + cls.DEFAULT_MESSAGE_TTL

        common_group_key = None
        for key in COMMON_GROUP_KEYS:
            if key in message_data:
                common_group_key = key
                break

        message_info = CB_MessageInfo(
            action=cls.DEFAULT_ACTION,
            perform_action_at=perform_action_at,
            common_group_key=common_group_key,
            content_type=content_type
        )
        message_data["cb_message_info"] = asdict(message_info)

        logger.info("Adding message: {}".format(message_data))
        add_result = db.NewMessagesCollection.add_document(message_data)
        if add_result:
            if not common_group_key or not db.NewMessagesCollection.exists_document_in_group(common_group_key, message_data[common_group_key]):
                add_result.data["need_reply"] = True
            logger.info("Saved new message with _id:[{}]".format(str(add_result.data["_id"])))
        else:
            logger.error(
                "Error occured while adding received message: {}".format(add_result.info)
            )

        return add_result


cls_strategy_by_content_type = {
    ContentType.TEXT: ContentStrategy,
    ContentType.PHOTO: ContentStrategy,
    ContentType.VIDEO: ContentStrategy,
    ContentType.ANIMATION: ContentStrategy,
    ContentType.AUDIO: ContentStrategy,
    ContentType.STICKER: ContentStrategy,
    ContentType.VIDEO_NOTE: ContentStrategy,
    ContentType.VOICE: ContentStrategy,
}


async def perform_message_action(message_id: str, *args):
    message_data = db.NewMessagesCollection.get_document(message_id)
    return await _perform_message_action(message_data, *args)


async def _perform_message_action(message_data: dict, bot: Bot):
    cb_message_info = CB_MessageInfo(message_data["cb_message_info"])
    cls_strategy = cls_strategy_by_content_type.get(cb_message_info.content_type, ContentStrategy)
    return await cls_strategy.perform_action(cb_message_info.action, message_data["_id"], bot)


async def check_actions_on_new_messages():
    filter_search = {"cb_message_info.perform_action_at": {"$lt": int(datetime.now().timestamp())}}
    messages = db.NewMessagesCollection.get_documents_by_filter(filter_search)

    for message in messages:
        cb_message_info = CB_MessageInfo(message["cb_message_info"])


########
#   Text:
#       - Dump
#       - Note
#       - ToDo
#       - Delete
#   Link:
#       - Dump
#       - Note
#       - Bookmark
#       - Delete
########
#   Photo:
#       - Save (all)
#       - Delete
#   Video:
#       - Save
#       - Delay save
#       - Delete
########
#   Video note:
#       - Save
#       - Delete
#   Voice:
#       - Save
#       - Delete
#   Music:
#       - Save
#       - Delete
#######
#   Sticker:
#       - Save
#       - Save all from stickerpack
#       - Delete
#######
#   Delete:
#       - Delete now
#       - Delete in 1 hour
#       - Delete tomorrow
#       - Reset delete timer
