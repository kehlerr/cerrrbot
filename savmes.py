import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from functools import partial
from typing import Any, Callable, Dict, List, Optional, Union

from aiogram import Bot
from aiogram.types import ContentType
from dacite import from_dict

import db_utils as db
from common import AppResult, create_directory
from settings import (
    DATA_DIRECTORY_ROOT,
    DELETE_TIMEOUT_1,
    DELETE_TIMEOUT_2,
    DELETE_TIMEOUT_3,
    TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION,
)

logger = logging.getLogger("cerrrbot")


class MessageActions(str, Enum):
    NONE = "NONE"
    DELETE_REQUEST = "DEL"
    SAVE = "SAVE"
    DOWNLOAD_FILE = "DL"
    DOWNLOAD_ALL = "DLAL"
    DOWNLOAD_DELAY = "DLDE"
    NOTE = "NOTE"
    TODO = "NOTO"
    BOOKMARK = "AB"
    DELETE_FROM_CHAT = "DFC"
    DELETE_NOW = "DELN"
    DELETE_1 = "DEL1"
    DELETE_2 = "DEL2"
    DELETE_3 = "DEL3"


@dataclass
class CB_MessageInfo:
    action: str = MessageActions.DELETE_NOW
    perform_action_at: int = 0
    common_group_key: Optional[str] = None
    content_type: str = ContentType.TEXT


async def set_action_message_id(document_message_id: str, action_message_id):
    return db.NewMessagesCollection.update_document(
        document_message_id, {"action_message_id": action_message_id}
    )


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
        result_ = await _perform_message_action(message_data, bot)
        result.merge(result_)

    return result


async def perform_message_action(message_id: str, *args):
    message_data, _ = _find_message(message_id)
    result = await _perform_message_action(message_data, *args)
    return result


async def _perform_message_action(message_data: dict, bot: Bot):
    cb_message_info = from_dict(
        data_class=CB_MessageInfo, data=message_data["cb_message_info"]
    )
    cls_strategy = cls_strategy_by_content_type.get(
        cb_message_info.content_type, ContentStrategy
    )
    action = cb_message_info.action
    message_document_id = message_data["_id"]

    result = await cls_strategy.perform_action(action, message_document_id, bot)
    logger.info(
        "[{}]Result performed action {}:{}".format(message_document_id, action, result)
    )
    return result


class ContentStrategy:
    DEFAULT_MESSAGE_TTL = TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION
    DEFAULT_ACTION = MessageActions.DELETE_1
    COMMON_GROUP_KEYS = {
        "media_group_id",
    }

    @classmethod
    async def perform_action(cls, action: str, message_id: str, bot: Bot) -> AppResult:
        action_method = cls._get_action_by_code(action)
        if not action_method:
            logger.error("Action method not found:{}".format(action))
            return AppResult(False)
        result = await action_method(message_id, bot)
        return result

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
        elif code == MessageActions.DELETE_1:
            return partial(cls._delete_after_time, DELETE_TIMEOUT_1)
        elif code == MessageActions.DELETE_2:
            return partial(cls._delete_after_time, DELETE_TIMEOUT_2)
        elif code == MessageActions.DELETE_3:
            return partial(cls._delete_after_time, DELETE_TIMEOUT_3)
        elif code == MessageActions.DELETE_FROM_CHAT:
            return cls._delete_from_chat
        elif code == MessageActions.DOWNLOAD_FILE:
            return cls.download
        elif code == MessageActions.DOWNLOAD_ALL:
            return cls.download_all

        return None

    @classmethod
    async def _delete_after_time(cls, timeout, message_id, *args) -> AppResult:
        return await update_action_for_message(
            message_id, MessageActions.DELETE_NOW, timeout
        )

    @classmethod
    async def save(self, message_id: str, bot: Bot) -> AppResult:
        message_data, collection = _find_message(message_id)
        if not message_data:
            return AppResult(False, "Message with id: {} not found".format(message_id))

        if collection != db.NewMessagesCollection:
            return AppResult(
                False,
                "Message with id: {} not in NewMessagesCollection".format(message_id),
            )

        save_result = db.SavedMessagesCollection.add_document(message_data)
        del_result = db.NewMessagesCollection.del_document(message_id)
        save_result.merge(del_result)
        if save_result:
            await update_action_for_message(message_id, MessageActions.NONE)
            save_result.data["next_actions"] = (
                MessageActions.DELETE_FROM_CHAT,
                MessageActions.NOTE,
            )
        return save_result

    @classmethod
    async def delete_request(cls, message_id: str, bot: Bot) -> AppResult:
        next_actions = (
            MessageActions.DELETE_1,
            MessageActions.DELETE_2,
            MessageActions.DELETE_3,
            MessageActions.DELETE_NOW,
        )
        return AppResult(True, data={"next_actions": next_actions})

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
    async def _delete_from_chat(
        cls, message_id: str, bot: Bot, message_data: Optional[dict] = None
    ) -> AppResult:
        if not message_data:
            message_data, _ = _find_message(message_id)
            if not message_data:
                return AppResult(False, "[{}] Message not found".format(message_id))

        chat_id = message_data["chat"]["id"]
        try:
            result = await bot.delete_message(
                chat_id, message_data["action_message_id"]
            )
            result = AppResult(result)
        except KeyError:
            logger.info(
                "[{}] Not found action message, no need to delete it".format(message_id)
            )
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
    async def add_new_message(
        cls, message_data: Dict[str, Any], content_type: ContentType
    ) -> AppResult:
        perform_action_at = int(datetime.now().timestamp()) + cls.DEFAULT_MESSAGE_TTL

        common_group_key = None
        for key in cls.COMMON_GROUP_KEYS:
            if key in message_data:
                common_group_key = key
                break

        message_info = CB_MessageInfo(
            action=cls.DEFAULT_ACTION,
            perform_action_at=perform_action_at,
            common_group_key=common_group_key,
            content_type=content_type,
        )
        message_data["cb_message_info"] = asdict(message_info)

        logger.info("Adding message: {}".format(message_data))
        add_result = db.NewMessagesCollection.add_document(message_data)
        if add_result:
            if (
                not common_group_key
                or not db.NewMessagesCollection.exists_document_in_group(
                    common_group_key, message_data[common_group_key]
                )
            ):
                add_result.data["need_reply"] = True
            logger.info(
                "Saved new message with _id:[{}]".format(str(add_result.data["_id"]))
            )
        else:
            logger.error(
                "Error occured while adding received message: {}".format(add_result)
            )

        return add_result

    @classmethod
    async def download(cls, *args):
        raise NotImplementedError


class _DownloadableContentStrategy(ContentStrategy):
    content_type_key: str
    file_extension: str
    sort_key: str = "height"

    @classmethod
    async def download(cls, message_id: str, bot: Bot) -> AppResult:
        message_data, _ = _find_message(message_id)
        if not message_data:
            return AppResult(False, "Message with id: {} not found".format(message_id))

        from_user = cls._get_from_user_id(message_data)
        from_chat = cls._get_from_chat_id(message_data)

        result = await cls._download(
            message_data[cls.content_type_key],
            bot,
            from_user=from_user,
            from_chat=from_chat,
        )
        if result:
            await update_action_for_message(message_id, MessageActions.NONE)
        return result

    @staticmethod
    def _get_from_chat_id(message_data: Dict[str, Any]) -> str:
        if "forward_from_chat" in message_data:
            from_chat = message_data["forward_from_chat"]
        elif "forward_from_user" in message_data:
            from_chat = message_data["forward_from_user"]
        else:
            from_chat = message_data["chat"]

        return str(from_chat["id"])

    @staticmethod
    def _get_from_user_id(message_data: Dict[str, Any]) -> str:
        from_user = message_data["from_user"]
        return str(from_user["id"])

    @classmethod
    async def _download(
        cls,
        downloadable_data: list[dict[Any]],
        bot: Bot,
        from_user: Optional[Dict[str, Any]] = "",
        from_chat: Optional[Dict[str, Any]] = "",
        dir_path: Optional[str] = None,
    ):

        file_data = cls._best_quality_variant(downloadable_data)
        if not file_data:
            return AppResult(
                False, "Wrong downloadable_data: {}".format(downloadable_data)
            )

        file_name = cls._get_file_name(file_data, from_user, from_chat)
        result = await _save_file(bot, file_data["file_id"], file_name, dir_path)
        return result

    @classmethod
    def _best_quality_variant(
        cls, variants_data: List[Any]
    ) -> Union[Dict[str, Any], None]:
        if isinstance(variants_data, dict):
            return variants_data

        sorted_variants = sorted(
            variants_data, key=lambda v: v[cls.sort_key], reverse=True
        )
        try:
            return sorted_variants[0]
        except IndexError:
            return None

    @classmethod
    def _get_file_name(
        cls, file_data: Dict[str, Any], from_user_id: str, from_chat_id: str
    ) -> str:
        file_unique_id = file_data["file_unique_id"]
        extension = cls._get_extension(file_data)
        file_name = f"{file_unique_id}.{extension}"
        if from_user_id and from_chat_id:
            file_name = f"{from_user_id}_{from_chat_id}-{file_name}"
        return file_name

    @classmethod
    def _get_extension(cls, file_data: Dict[str, Any]) -> str:
        return cls.file_extension


class PhotoContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.PHOTO
    file_extension: str = "jpg"


class VideoContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.VIDEO
    file_extension: str = "mp4"


class AnimationContentStrategy(_DownloadableContentStrategy):
    file_extension: str = "mp4"
    content_type_key: str = ContentType.ANIMATION


class AudioContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.AUDIO
    file_extension: str = "mp3"


class VideonoteContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.VIDEO_NOTE
    file_extension: str = "mp4"


class VoiceContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.VOICE
    file_extension: str = "ogg"


class StickerContentStrategy(_DownloadableContentStrategy):
    file_extension: str = "webp"
    content_type_key: str = ContentType.STICKER

    @classmethod
    async def download_all(cls, message_id: str, bot: Bot) -> AppResult:
        message_data, _ = _find_message(message_id)
        if not message_data:
            return AppResult(False, "Message with id: {} not found".format(message_id))

        sticker_set_name = message_data[cls.content_type_key]["set_name"]
        sticker_set = await bot.get_sticker_set(sticker_set_name)
        result = create_directory(sticker_set_name)
        if not result:
            return result

        for sticker in sticker_set.stickers:
            result_ = await cls._download(
                json.loads(sticker.json()), bot, dir_path=result.data
            )
            result.merge(result_)

        if result:
            await update_action_for_message(message_id, MessageActions.NONE)

        return result

    @classmethod
    def _get_extension(cls, file_data: Dict[str, Any]) -> str:
        if file_data.get("is_video"):
            return "webm"

        return super()._get_extension(file_data)

    @staticmethod
    def _get_from_user_id(*args) -> str:
        return ""

    @staticmethod
    def _get_from_chat_id(*args) -> str:
        return ""


cls_strategy_by_content_type = {
    ContentType.TEXT: ContentStrategy,
    ContentType.PHOTO: PhotoContentStrategy,
    ContentType.VIDEO: VideoContentStrategy,
    ContentType.ANIMATION: AnimationContentStrategy,
    ContentType.AUDIO: AudioContentStrategy,
    ContentType.STICKER: StickerContentStrategy,
    ContentType.VIDEO_NOTE: VideonoteContentStrategy,
    ContentType.VOICE: VoiceContentStrategy,
    ContentType.DOCUMENT: ContentStrategy,
}


async def _save_file(
    bot: Bot, file_id: str, file_name: str, dir_path: str
) -> AppResult:
    if not dir_path:
        dir_path = DATA_DIRECTORY_ROOT

    file_path = os.path.join(dir_path, file_name)
    try:
        await bot.download(file_id, file_path)
    except Exception as exc:
        logger.error(exc)
        return AppResult(False, exc)

    return AppResult()


async def update_action_for_message(
    message_id: str, new_action: str, new_ttl: Optional[int] = None
):
    message_data, collection = _find_message(message_id)
    cb_message_info = from_dict(
        data_class=CB_MessageInfo, data=message_data["cb_message_info"]
    )
    cb_message_info.action = new_action
    if new_ttl is not None:
        perform_action_at = int(datetime.now().timestamp()) + new_ttl
        cb_message_info.perform_action_at = perform_action_at

    if new_action == MessageActions.NONE:
        cb_message_info.perform_action_at = -1

    updated_data = asdict(cb_message_info)
    return collection.update_document(message_id, {"cb_message_info": updated_data})


def _find_message(message_id: str):
    collections = {db.NewMessagesCollection, db.SavedMessagesCollection}
    for collection in collections:
        message = collection.get_document(message_id)
        if message:
            return message, collection

    return None, None
