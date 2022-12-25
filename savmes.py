import logging
from enum import Enum
from functools import partial
from typing import Any, Dict, Optional, Callable, Union
from dataclasses import dataclass, asdict
from dacite import from_dict
from datetime import datetime

from aiogram import Bot
from aiogram.types import ContentType, Message

import db_utils as db
from common import AppResult


logger = logging.getLogger(__name__)
logger = logging.getLogger("__main__")


class MessageActions(str, Enum):
    NONE = "NONE"
    DELETE_REQUEST = "Delete"
    SAVE = "Save"
    DOWNLOAD_FILE = "Download"
    DOWNLOAD_ALL = "Download all"
    DOWNLOAD_DELAY = "Download delay"
    NOTE = "Note"
    TODO = "Note ToDo"
    BOOKMARK = "Add bookmark"
    DELETE_FROM_CHAT = "Delete from chat"
    DELETE_NOW = "Delete now"
    DELETE_30_MIN = "Delete in 30 min"
    DELETE_12_HRS = "Delete in 12 hours"
    DELETE_48_HRS = "Delete in 48 hours"


@dataclass
class CB_MessageInfo:
    action: str = MessageActions.DELETE_NOW
    perform_action_at: int = 0
    common_group_key: Optional[str] = None
    content_type: str = ContentType.TEXT


COMMON_GROUP_KEYS = {"media_group_id",}


async def update_action_for_message(message_id: str, new_action: str, new_ttl: Optional[int] = None):
    message_data, collection = _find_message(message_id)
    cb_message_info = from_dict(data_class=CB_MessageInfo, data=message_data["cb_message_info"])
    cb_message_info.action = new_action
    if new_ttl is not None:
        perform_action_at = int(datetime.now().timestamp()) + new_ttl
        cb_message_info.perform_action_at = perform_action_at

    if new_action == MessageActions.NONE:
        cb_message_info.perform_action_at = -1

    updated_data = asdict(cb_message_info)
    return collection.update_document(message_id, {"cb_message_info": updated_data})


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
    DEFAULT_MESSAGE_TTL = 10
    DEFAULT_ACTION = MessageActions.DELETE_30_MIN

    @classmethod
    async def perform_action(cls, action: str, message_id: str, bot: Bot) -> AppResult:
        action_method = cls._get_action_by_code(action)
        if not action_method:
            logger.error("Action method not found:{}".format(action))
            return AppResult(False)
        result = await action_method(message_id, bot)
        return result

    @classmethod
    async def download(cls, *args):
        raise NotImplementedError

    @classmethod
    def _get_action_by_code(cls, code: MessageActions) -> Optional[Callable]:
        if code == MessageActions.SAVE:
            return cls.save
        elif code == MessageActions.DELETE_REQUEST:
            return cls.delete_request
        elif code == MessageActions.DELETE_NOW:
            return cls.delete
        elif code == MessageActions.NOTE:
            return cls.delete
        elif code == MessageActions.DELETE_30_MIN:
            return partial(cls._delete_after_time, 30)
        elif code == MessageActions.DELETE_12_HRS:
            return partial(cls._delete_after_time, 30)
        elif code == MessageActions.DELETE_48_HRS:
            return partial(cls._delete_after_time, 30)
        elif code == MessageActions.DELETE_FROM_CHAT:
            return cls._delete_from_chat
        elif code == MessageActions.DOWNLOAD_FILE:
            return cls.download

        return None

    @classmethod
    async def _delete_after_time(cls, timeout, message_id, *args) -> AppResult:
        return await update_action_for_message(message_id, MessageActions.DELETE_NOW, timeout)

    @classmethod
    async def save(self, message_id: str, bot: Bot) -> AppResult:
        message_data, collection = _find_message(message_id)
        if not message_data:
            return AppResult(False, "Message with id: {} not found".format(message_id))

        if collection != db.NewMessagesCollection:
            return AppResult(False, "Message with id: {} not in NewMessagesCollection".format(message_id))

        save_result = db.SavedMessagesCollection.add_document(message_data)
        del_result = db.NewMessagesCollection.del_document(message_id)
        save_result.merge(del_result)
        if save_result:
            await update_action_for_message(message_id, MessageActions.NONE)
            save_result.data["next_actions"] = (MessageActions.DELETE_FROM_CHAT, MessageActions.NOTE)
        return save_result

    @classmethod
    async def delete_request(self, message_id: str, bot: Bot) -> AppResult:
        next_actions = (
            MessageActions.DELETE_NOW,
            MessageActions.DELETE_30_MIN,
            MessageActions.DELETE_12_HRS,
            MessageActions.DELETE_48_HRS
        )
        return AppResult(True, data = {"next_actions": next_actions})

    @classmethod
    async def delete(cls, message_id: str, bot: Bot) -> AppResult:
        message_data, _ = _find_message(message_id)
        if not message_data:
            return AppResult(False, "[{}] Message not found".format(message_id))

        result = db.NewMessagesCollection.del_document(message_id)
        if result:
            result = await cls._delete_from_chat(message_id, bot, message_data)

        logger.info(result)
        return result

    @classmethod
    async def _delete_from_chat(cls, message_id: str, bot: Bot, message_data: Optional[dict] = None) -> AppResult:
        if not message_data:
            message_data, _ = _find_message(message_id)
            if not message_data:
                return AppResult(False, "[{}] Message not found".format(message_id))

        chat_id = message_data["chat"]["id"]
        try:
            result = await bot.delete_message(chat_id, message_data["action_message_id"])
            result = AppResult(result)
        except KeyError:
            logger.info("[{}] Not found action message, no need to delete it".format(message_id))
        except Exception as exc:
            logger.error(exc)
            result = AppResult(False, str(exc))

        try:
            result_ = await bot.delete_message(chat_id, message_data["message_id"])
            result_deleting_message = AppResult(result_)
        except Exception as exc:
            logger.error(exc)
            result_deleting_message = AppResult(False, str(exc))

        result.merge(result_deleting_message)

        return result

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
                "Error occured while adding received message: {}".format(add_result)
            )

        return add_result

class StickerContentStrategy(ContentStrategy):

    @classmethod
    async def download(cls, message_id: str, bot: Bot) -> AppResult:
        message_data, _ = _find_message(message_id)
        if not message_data:
            return AppResult(False, "Message with id: {} not found".format(message_id))

        file_path = message_data["sticker"]["file_id"]
        file_unique_id = message_data["sticker"]["file_unique_id"]
        extension = "webp"
        file_name = f"{file_unique_id}.{extension}"
        try:
            await bot.download(file_path, file_name)
        except Exception as exc:
            logger.error(exc)
            result = AppResult(False, exc)
        else:
            result = AppResult(True)

        if result:
            await update_action_for_message(message_id, MessageActions.NONE)

        return result

    @classmethod
    async def download_all(cls, message_id: str, bot: Bot) -> AppResult:
        
        

cls_strategy_by_content_type = {
    ContentType.TEXT: ContentStrategy,
    ContentType.PHOTO: ContentStrategy,
    ContentType.VIDEO: ContentStrategy,
    ContentType.ANIMATION: ContentStrategy,
    ContentType.AUDIO: ContentStrategy,
    ContentType.STICKER: StickerContentStrategy,
    ContentType.VIDEO_NOTE: ContentStrategy,
    ContentType.VOICE: ContentStrategy,
}


async def perform_message_action(message_id: str, *args):
    message_data, _ = _find_message(message_id)
    result = await _perform_message_action(message_data, *args)
    return result


async def check_actions_on_new_messages(bot: Bot):
    filter_search = {
        "cb_message_info.perform_action_at": {
            "$lt": int(datetime.now().timestamp()),
            "$gt": 0
        }
    }
    messages = db.NewMessagesCollection.get_documents_by_filter(filter_search)
    for message_data in messages:
        result = await _perform_message_action(message_data, bot)


async def _perform_message_action(message_data: dict, bot: Bot):
    cb_message_info = from_dict(data_class=CB_MessageInfo, data=message_data["cb_message_info"])
    cls_strategy = cls_strategy_by_content_type.get(cb_message_info.content_type, ContentStrategy)
    action = cb_message_info.action
    message_document_id = message_data["_id"]

    result = await cls_strategy.perform_action(action,message_document_id, bot)
    logger.info("[{}]Result performed action {}:{}".format(message_document_id, action, result))
    return result


def _find_message(message_id: str):
    collections = {db.NewMessagesCollection, db.SavedMessagesCollection}
    for collection in collections:
        message = collection.get_document(message_id)
        if message:
            return message, collection


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
