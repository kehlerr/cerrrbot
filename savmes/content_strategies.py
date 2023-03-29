import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

from aiogram import Bot
from aiogram.types import ContentType
from celery import signature, states
from celery.result import AsyncResult as CeleryTaskResult

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from common import AppResult, create_directory
from tasks import app

from .common import (
    CustomMessageAction,
    MessageActions,
    SVM_MsgdocInfo,
    SVM_ReplyInfo,
    save_file,
)
from .constants import COMMON_GROUP_KEY
from .content_strategy_base import ContentStrategyBase
from .message_document import MessageDocument

logger = logging.getLogger("cerrrbot")


class ContentStrategy(ContentStrategyBase):
    @classmethod
    async def perform_action(
        cls, action_code: str, msgdoc: MessageDocument, bot: Bot
    ) -> AppResult:
        action = MessageActions.ACTION_BY_CODE.get(action_code)
        if not action:
            logger.error(f"Action not found: {action_code}")
            return AppResult(False)

        try:
            action_method = getattr(cls, action.method)
        except AttributeError:
            logger.error(f"Action method not found:{action.method}")
            return AppResult(False)

        result = await action_method(msgdoc, bot, **action.method_args)
        if result:
            cls._prepare_reply_info(msgdoc.cb_message_info, result.data)
        logger.info(f"Result of performed action:{result}")
        return result

    @classmethod
    async def custom_task(
        cls, msgdoc: MessageDocument, bot: Bot, *args, **task_info
    ) -> AppResult:
        action_code = task_info["code"]
        action = MessageActions.ACTION_BY_CODE[action_code]
        action_data = msgdoc.cb_message_info.actions[action_code]
        task_id = action_data.get("task_id")
        if task_id:
            result = cls._get_task_reply(task_id, action, msgdoc)
        else:
            result = cls._create_task(task_info, action_data["data"], action, msgdoc)
        return result

    @classmethod
    def _create_task(
        cls,
        task_info: str,
        task_args: Dict[str, Any],
        action: CustomMessageAction,
        msgdoc: MessageDocument,
    ) -> AppResult:
        task_name = task_info["task_name"]
        task_signature = signature(f"tasks.savmes_tasks.{task_name}")
        if task_info.get("is_instant", False):
            task_signature(task_args, msgdoc)
            return cls._update_actions(msgdoc, (action,))

        try:
            result = task_signature.delay(task_args)
            task_id = str(result)
            task_status = CeleryTaskResult(task_id, app=app).status
        except Exception as exc:
            logger.exception(exc)
            return AppResult(False)

        result_data = {
            "task_id": task_id,
            "additional_caption": f" [{task_status}]",
        }

        result = cls._update_actions(msgdoc, to_add={action: result_data})
        return result

    @classmethod
    def _get_task_reply(
        cls, task_id: str, action: CustomMessageAction, msgdoc: MessageDocument
    ) -> AppResult:
        task_result = CeleryTaskResult(task_id, app=app)
        status = task_result.status
        reply_info = SVM_ReplyInfo(popup_text=status)
        if status == states.SUCCESS:
            result = cls._update_actions(msgdoc, (action,))
            reply_info.actions = msgdoc.cb_message_info.actions
        else:
            result = AppResult()
            reply_info.need_edit_buttons = False
        result.data["reply_info"] = reply_info

        return result

    @classmethod
    async def save(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        del_result = msgdoc.delete()
        if not del_result:
            return del_result

        result = msgdoc.add_to_collection()
        if result:
            result = cls._update_actions(
                msgdoc,
                (MessageActions.SAVE, MessageActions.DELETE_REQUEST),
                {MessageActions.DELETE_FROM_CHAT: None},
            )
        return result

    @classmethod
    async def delete_request(cls, *args, **kwargs) -> AppResult:
        reply_info = SVM_ReplyInfo(
            actions={
                MessageActions.DELETE_1,
                MessageActions.DELETE_2,
                MessageActions.DELETE_3,
                MessageActions.DELETE_NOW,
            }
        )
        return AppResult(True, data={"reply_info": reply_info})

    @classmethod
    async def delete(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        result = msgdoc.delete()
        if result:
            result = await cls.delete_from_chat(msgdoc, bot)
        return result

    @classmethod
    async def delete_from_chat(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        result = AppResult()
        try:
            result = await bot.delete_message(
                msgdoc.chat.id, msgdoc.cb_message_info.reply_action_message_id
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
            result_ = await bot.delete_message(msgdoc.chat.id, msgdoc.message_id)
        except Exception as exc:
            logger.error(exc)
            result_ = AppResult(False, str(exc))

        result.merge(result_)
        result.data.update({"reply_info": SVM_ReplyInfo()})
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


class _DownloadableContentStrategy(ContentStrategy):
    content_type_key: str
    file_extension: str
    sort_key: str = "height"

    POSSIBLE_ACTIONS = {MessageActions.DELETE_REQUEST, MessageActions.DOWNLOAD_FILE}

    @classmethod
    def _prepare_message_info(cls, message_data: Dict[str, Any]) -> SVM_MsgdocInfo:
        message_info = super()._prepare_message_info(message_data)
        message_actions = message_info.actions
        if message_actions and COMMON_GROUP_KEY in message_data:
            message_actions.pop(MessageActions.DOWNLOAD_FILE.code)
            message_actions[MessageActions.DOWNLOAD_ALL.code] = {}
        return message_info

    @classmethod
    async def delete(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        msgdocs = msgdoc.get_msgdocs_by_group()
        if not msgdocs:
            result = await super().delete(msgdoc, bot)
            return result

        result = AppResult()
        for msgdoc_ in msgdocs:
            result_ = await super().delete(msgdoc_, bot)
            result.merge(result_)
        return result

    @classmethod
    async def download(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        result = await cls._download(msgdoc, bot)
        if result:
            result = cls._update_actions(msgdoc, (MessageActions.DOWNLOAD_FILE,))
        return result

    @classmethod
    async def download_all(cls, msgdoc: MessageDocument, bot: Bot):
        result = AppResult()
        for _msgdoc in msgdoc.get_msgdocs_by_group():
            _cls = cls_strategy_by_content_type[_msgdoc.content_type]
            _result = await _cls._download(_msgdoc, bot)
            result.merge(_result)

        if result:
            result = cls._update_actions(msgdoc, (MessageActions.DOWNLOAD_ALL,))
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
