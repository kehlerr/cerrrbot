import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from aiogram import Bot
from aiogram.types import ContentType, Message
from celery import signature

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import db_utils as db
from common import AppResult, create_directory
from settings import TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION
from trilium_helper import add_bookmark_urls, add_note

from .common import CB_MessageInfo, save_file
from .constants import MessageAction, MessageActions
from .message_document import MessageDocument
from .message_parser import MessageParser

logger = logging.getLogger("cerrrbot")


class ContentStrategy:
    DEFAULT_MESSAGE_TTL = TIMEOUT_BEFORE_PERFORMING_DEFAULT_ACTION
    DEFAULT_ACTION = MessageActions.DELETE_1
    COMMON_GROUP_KEY = "media_group_id"

    POSSIBLE_ACTIONS = {
        MessageActions.SAVE,
        MessageActions.NOTE,
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
            add_result.data["message_info"] = message_info
        else:
            logger.error(
                "Error occured while adding received message: {}".format(add_result)
            )
        return add_result

    @classmethod
    def _prepare_message_info(cls, message_data: Dict[str, Any]) -> CB_MessageInfo:
        message_info = CB_MessageInfo(
            action=cls.DEFAULT_ACTION,
            entities=message_data.get("caption_entities")
            or message_data.get("entities", []),
        )
        common_group_id = message_data.get(cls.COMMON_GROUP_KEY)
        if (
            not common_group_id
            or not db.NewMessagesCollection.exists_document_in_group(
                cls.COMMON_GROUP_KEY, common_group_id
            )
        ):
            message_info.actions = {action.code: {} for action in cls.POSSIBLE_ACTIONS}
            cls._parse_message(message_data, message_info)
        return message_info

    @classmethod
    def _parse_message(
        cls, message_data: Dict[str, Any], message_info: CB_MessageInfo
    ) -> None:
        parser = MessageParser(message_data["text"], message_info)
        parser.parse()
        message_info.actions.update(parser.actions)

    @classmethod
    async def perform_action(
        cls, action_code: str, msgdoc: MessageDocument, bot: Bot
    ) -> AppResult:
        action = MessageActions.ACTION_BY_CODE.get(action_code)
        if not action:
            logger.error("Action not found: {}".format(action_code))
            return AppResult(False)

        try:
            action_method = getattr(cls, action.method)
        except AttributeError:
            logger.error("Action method not found:{}".format(action.method))
            return AppResult(False)

        result = await action_method(msgdoc, bot, **action.method_args)
        if "message_info" not in result.data:
            result.data["message_info"] = msgdoc.cb_message_info

        logger.info(f"Result of performed action:{result}")
        return result

    @classmethod
    async def custom_task(
        cls, msgdoc: MessageDocument, bot: Bot, *args, **kwargs
    ) -> AppResult:
        added_task_data = {}

        action_code = kwargs["code"]
        task_data = msgdoc.cb_message_info.actions[action_code]
        task_id = task_data.get("task_id")
        if not task_id:
            task_id = cls._run_task(kwargs["task_name"], task_data)
            if not task_id:
                return AppResult(False)
        else:
            added_task_data["result_info"] = "Task is in progress"

        action = MessageActions.ACTION_BY_CODE[action_code]
        added_task_data.update(
            {"additional_caption": "[in progress]", "task_id": str(task_id)}
        )
        result = cls._update_actions(msgdoc, to_add={action: added_task_data})

        return result

    @classmethod
    def _run_task(cls, task_name: str, task_data: Dict[str, Any]) -> Optional[str]:
        try:
            task_signature = signature(f"tasks.savmes_tasks.{task_name}")
            result = task_signature.delay(task_data["data"])
        except Exception as exc:
            logger.exception(exc)
            return None

        return str(result)

    @classmethod
    async def save(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        del_result = msgdoc.delete()
        if not del_result:
            return del_result

        result = msgdoc.add(db.SavedMessagesCollection)
        if result:
            result = cls._update_actions(
                msgdoc,
                (MessageActions.SAVE, MessageActions.DELETE_REQUEST),
                {MessageActions.DELETE_FROM_CHAT: None},
            )
        return result

    @classmethod
    async def note_bookmark_url(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        text_links = [
            e["url"]
            for e in msgdoc.cb_message_info.entities
            if e["type"] == "text_link"
        ]
        result = AppResult(add_bookmark_urls(msgdoc.message_text, text_links))
        if result:
            result = cls._update_actions(msgdoc, (MessageActions.BOOKMARK,))
        return result

    @classmethod
    async def add_note(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        forward_from_id, title = msgdoc.get_from_chat_data()
        if not forward_from_id:
            forward_from_id, title = msgdoc.get_from_user_data()

        result = AppResult(add_note(msgdoc.message_text, forward_from_id, title))
        if result:
            result = cls._update_actions(msgdoc, (MessageActions.NOTE,))

        return result

    @classmethod
    async def delete_request(cls, *args, **kwargs) -> AppResult:
        message_info = CB_MessageInfo(
            actions={
                MessageActions.DELETE_1.code: {},
                MessageActions.DELETE_2.code: {},
                MessageActions.DELETE_3.code: {},
                MessageActions.DELETE_NOW.code: {},
            }
        )
        return AppResult(True, data={"message_info": message_info})

    @classmethod
    async def delete(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        result = msgdoc.delete()
        if result:
            result = await cls.delete_from_chat(msgdoc, bot)
            result.data.update({"message_info": None})
        return result

    @classmethod
    async def delete_from_chat(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        result = AppResult()
        chat_id = msgdoc.chat.id
        try:
            result = await bot.delete_message(
                chat_id, msgdoc.cb_message_info.reply_action_message_id
            )
            result = AppResult(result)
        except AttributeError:
            logger.info(
                "[{}] Not found action message, no need to delete it".format(msgdoc._id)
            )
        except Exception as exc:
            logger.error(exc)
            result = AppResult(False, str(exc))

        try:
            result_ = await bot.delete_message(chat_id, msgdoc.message_id)
            result_deleting_message = AppResult(result_, data={"message_info": None})
        except Exception as exc:
            logger.error(exc)
            result_deleting_message = AppResult(False, str(exc))
        result.merge(result_deleting_message)

        result.data.update({"message_info": None})

        return result

    @classmethod
    async def _delete_after_time(
        cls, msgdoc: MessageDocument, bot: Bot, timeout: int
    ) -> AppResult:
        return msgdoc.update_message_info(MessageActions.DELETE_NOW, new_ttl=timeout)

    @classmethod
    async def download(cls, *args):
        raise NotImplementedError

    @classmethod
    async def download_all(cls, *args):
        raise NotImplementedError

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


class _DownloadableContentStrategy(ContentStrategy):
    content_type_key: str
    file_extension: str
    sort_key: str = "height"

    POSSIBLE_ACTIONS = {MessageActions.DELETE_REQUEST, MessageActions.DOWNLOAD_FILE}

    @classmethod
    def _prepare_message_info(cls, message_data: Dict[str, Any]) -> CB_MessageInfo:
        message_info = super()._prepare_message_info(message_data)
        message_actions = message_info.actions
        if message_actions and cls.COMMON_GROUP_KEY in message_data:
            message_actions.pop(MessageActions.DOWNLOAD_FILE.code)
            message_actions[MessageActions.DOWNLOAD_ALL.code] = {}

        if message_data.get("caption"):
            message_actions[MessageActions.NOTE.code] = {}
        return message_info

    @classmethod
    async def download_all(cls, msgdoc: MessageDocument, bot: Bot):
        result = AppResult()
        for _msgdoc in cls._get_messages_by_group(msgdoc):
            _cls = cls_strategy_by_content_type[_msgdoc.content_type]
            _result = await _cls._download(_msgdoc, bot)
            result.merge(_result)

        if result:
            result = cls._update_actions(msgdoc, (MessageActions.DOWNLOAD_ALL,))
        return result

    @classmethod
    async def download(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        result = await cls._download(msgdoc, bot)
        if result:
            result = cls._update_actions(msgdoc, (MessageActions.DOWNLOAD_FILE,))
        return result

    @classmethod
    async def _download(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        from_user, _ = msgdoc.get_from_user_data()
        from_chat, _ = msgdoc.get_from_chat_data()

        result = await cls._download_file_impl(
            getattr(msgdoc, cls.content_type_key),
            bot,
            from_user=from_user,
            from_chat=from_chat,
        )
        return result

    @classmethod
    async def _download_file_impl(
        cls,
        downloadable: list[Any],
        bot: Bot,
        from_user: Optional[Dict[str, Any]] = "",
        from_chat: Optional[Dict[str, Any]] = "",
        dir_path: Optional[str] = None,
    ):

        file_data = cls._best_quality_variant(downloadable)
        if not file_data:
            return AppResult(False, "Wrong downloadable_data: {}".format(downloadable))

        file_name = cls._get_file_name(file_data, from_user, from_chat)
        result = await save_file(bot, file_data.file_id, file_name, dir_path)
        return result

    @classmethod
    def _best_quality_variant(
        cls, variants_data: List[Any]
    ) -> Union[Dict[str, Any], None]:
        return variants_data

    @classmethod
    def _get_file_name(
        cls, file_data: Dict[str, Any], from_user_id: str, from_chat_id: str
    ) -> str:
        extension = cls._get_extension(file_data)
        file_name = f"{file_data.file_unique_id}.{extension}"
        if from_user_id and from_chat_id:
            file_name = f"{from_user_id}_{from_chat_id}-{file_name}"
        return file_name

    @classmethod
    def _get_extension(cls, *args) -> str:
        return cls.file_extension

    @classmethod
    def _get_messages_by_group(cls, msgdoc: MessageDocument) -> List[MessageDocument]:
        filter_search = {cls.COMMON_GROUP_KEY: getattr(msgdoc, cls.COMMON_GROUP_KEY)}
        return (
            MessageDocument(md["_id"])
            for md in db.NewMessagesCollection.get_documents_by_filter(filter_search)
        )


class PhotoContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.PHOTO
    file_extension: str = "jpg"
    POSSIBLE_ACTIONS = {MessageActions.DOWNLOAD_FILE, MessageActions.DELETE_REQUEST}

    @classmethod
    def _best_quality_variant(
        cls, variants_data: List[Any]
    ) -> Union[Dict[str, Any], None]:
        sorted_variants = sorted(
            variants_data, key=lambda v: getattr(v, cls.sort_key), reverse=True
        )
        return sorted_variants and sorted_variants[0]


class VideoContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.VIDEO
    file_extension: str = "mp4"
    POSSIBLE_ACTIONS = {MessageActions.DOWNLOAD_FILE, MessageActions.DELETE_REQUEST}


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
    POSSIBLE_ACTIONS = {
        MessageActions.DOWNLOAD_FILE,
        MessageActions.DOWNLOAD_ALL,
        MessageActions.DELETE_REQUEST,
    }

    @classmethod
    async def download_all(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        sticker_set_name = msgdoc.sticker.set_name
        sticker_set = await bot.get_sticker_set(sticker_set_name)
        result = create_directory(sticker_set_name)
        if not result:
            return result

        for sticker in sticker_set.stickers:
            result_ = await cls._download_file_impl(
                sticker, bot, dir_path=result.data["path"]
            )
            result.merge(result_)

        if result:
            result = cls._update_actions(msgdoc, (MessageActions.DOWNLOAD_ALL,))
        return result

    @classmethod
    def _get_extension(cls, file_data: Any) -> str:
        return "webm" if file_data.is_video else super()._get_extension(file_data)

    @staticmethod
    def _get_from_user_data(*args) -> Tuple[str, str]:
        return "", ""

    @staticmethod
    def _get_from_chat_id(*args) -> Tuple[str, str]:
        return "", ""


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
