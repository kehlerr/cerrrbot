import logging
import os
from typing import Any, Optional, Union

from aiogram import Bot
from aiogram.types import ContentType
from celery import signature, states
from celery.result import AsyncResult as CeleryTaskResult

from common import AppResult, save_file
from models import CustomMessageAction
from celery_app import app

from .actions import MessageActions
from .message_document_info import SVM_MsgdocInfo, SVM_ReplyInfo
from .constants import COMMON_GROUP_KEY, MAX_LOAD_FILE_SIZE
from .content_strategy_base import ContentStrategyBase
from .message_document import MessageDocument

logger = logging.getLogger("cerrrbot")


class ContentStrategy(ContentStrategyBase):
    @classmethod
    async def perform_action(
        cls, action_code: str, msgdoc: MessageDocument, bot: Bot
    ) -> AppResult:
        action = MessageActions.BY_CODE.get(action_code)
        if not action:
            logger.error(f"Action not found: {action_code}")
            return AppResult(False)

        try:
            action_method = getattr(cls, action.method)
        except AttributeError:
            logger.error(f"Action method not found:{action.method}")
            return AppResult(False)

        logger.info(f"Performing action: {action_code} with method: {action.method}")
        result = await action_method(msgdoc, bot, **action.method_args)
        if result:
            cls._prepare_reply_info(msgdoc.cb_message_info, result.data)
        logger.info(f"Result of performed action:{result}")
        return result

    @classmethod
    async def custom_task(cls, msgdoc: MessageDocument, *args, **task_info) -> AppResult:
        action_code = task_info["code"]
        action = MessageActions.BY_CODE[action_code]
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
        task_info: dict[str, Any],
        task_args: dict[str, Any],
        action: CustomMessageAction,
        msgdoc: MessageDocument,
    ) -> AppResult:
        task_signature = signature(task_info["task_name"])
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

        return cls._update_actions(msgdoc, to_add={action: result_data})

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
    async def keep(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        del_result = msgdoc.delete()
        if not del_result:
            return del_result

        result = await cls.delete_reply_message(msgdoc, bot)
        if not result:
            return result

        result.merge(msgdoc.add_to_collection())
        return result

    @classmethod
    async def delete_request(cls, msgdoc: MessageDocument, *args, **kwargs) -> AppResult:
        result = msgdoc.update_message_info(MessageActions.NONE)
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
        result = await cls.delete_reply_message(msgdoc, bot)
        try:
            result_ = await bot.delete_message(msgdoc.chat.id, msgdoc.message_id)
            result_ = AppResult()
        except Exception as exc:
            logger.error(exc)
            result_ = AppResult(False, str(exc))

        result.merge(result_)
        result.data.update({"reply_info": SVM_ReplyInfo(need_edit_buttons=False)})
        return result

    @classmethod
    async def delete_reply_message(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        message_id = msgdoc.cb_message_info.reply_action_message_id
        if not message_id:
            return AppResult()

        try:
            result = await bot.delete_message(msgdoc.chat.id, message_id)
            result = AppResult(result)
        except AttributeError:
            logger.warning(
                "[{}] Not found action message, no need to delete it".format(msgdoc._id)
            )
            result = AppResult()
        except Exception as exc:
            logger.error(exc)
            return AppResult(False, str(exc))

        if msgdoc.collection:
            result_ = msgdoc.update_message_info(None, new_actions={}, reply_action_message_id=0)
            result.merge(result_)

        result.data.update({"reply_info": SVM_ReplyInfo(actions={})})
        return result

    @classmethod
    async def _delete_after_time(
        cls, msgdoc: MessageDocument, bot: Bot, timeout: int
    ) -> AppResult:
        result = msgdoc.update_message_info(MessageActions.DELETE_NOW, new_ttl=timeout)
        result.data.update({"reply_info": SVM_ReplyInfo(need_edit_buttons=False)})
        return result

    @classmethod
    async def download(cls, *args):
        raise NotImplementedError

    @classmethod
    async def download_all(cls, *args) -> AppResult:
        return await cls.download(*args)


class _DownloadableContentStrategy(ContentStrategy):
    content_type_key: str
    file_extension: str = ""
    sort_key: str = "height"

    DEFAULT_ACTION = MessageActions.KEEP
    POSSIBLE_ACTIONS = {MessageActions.KEEP, MessageActions.DELETE_REQUEST, MessageActions.DOWNLOAD}

    @classmethod
    def _prepare_message_info(cls, message_data: dict[str, Any]) -> SVM_MsgdocInfo:
        message_info = super()._prepare_message_info(message_data)
        message_actions = message_info.actions
        fsize = 0 if cls.content_type_key == ContentType.PHOTO else message_data[cls.content_type_key]["file_size"]
        if fsize < MAX_LOAD_FILE_SIZE:
            message_info.action = MessageActions.DOWNLOAD
            if message_actions and COMMON_GROUP_KEY in message_data:
                message_actions.pop(MessageActions.DOWNLOAD.code, None)
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
        result = AppResult()
        msgdocs = msgdoc.get_msgdocs_by_group()
        if msgdocs:
            for _msgdoc in msgdocs:
               _cls = cls_strategy_by_content_type[_msgdoc.content_type]
               _result = await _cls._download(_msgdoc, bot)
               result.merge(_result)
        else:
            result = await cls._download(msgdoc, bot)

        if result:
            result = cls._update_actions(msgdoc, (MessageActions.DOWNLOAD, MessageActions.DOWNLOAD_ALL))
        return result

    @classmethod
    async def _download(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        from_user, _ = msgdoc.get_from_user_data()
        from_chat, _ = msgdoc.get_from_chat_data()
        return await cls._download_file_impl(
            getattr(msgdoc, cls.content_type_key),
            bot,
            from_user=from_user,
            from_chat=from_chat,
        )

    @classmethod
    async def _download_file_impl(
        cls,
        downloadable: list[Any],
        bot: Bot,
        from_user: Optional[str] = "",
        from_chat: Optional[str] = "",
        dir_name: Optional[str] = "",
    ) -> AppResult:

        file_data = cls._best_quality_variant(downloadable)
        if not file_data:
            return AppResult(False, "Wrong downloadable_data: {}".format(downloadable))

        dir_path = os.path.join(str(from_user), dir_name)
        file_name = cls._get_file_name(file_data, from_user, from_chat)
        return await save_file(bot, file_data.file_id, file_name, dir_path)

    @classmethod
    def _best_quality_variant(
        cls, variants_data: list[Any]
    ) -> Union[dict[str, Any], None]:
        return variants_data

    @classmethod
    def _get_file_name(
        cls, file_data: dict[str, Any], from_user_id: str, from_chat_id: str
    ) -> str:
        extension = cls._get_extension(file_data)
        file_name = f"{file_data.file_unique_id}"
        extension = cls._get_extension(file_data)
        if extension:
            file_name = f"{file_name}.{extension}"
        if from_user_id and from_chat_id:
            file_name = f"{from_user_id}_{from_chat_id}-{file_name}"
        return file_name

    @classmethod
    def _get_extension(cls, *args) -> str:
        return cls.file_extension


class PhotoContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.PHOTO
    file_extension: str = "jpg"

    @classmethod
    def _best_quality_variant(cls, variants_data: list[Any]) -> Optional[dict[str, Any]]:
        sorted_variants = sorted(variants_data, key=lambda v: getattr(v, cls.sort_key), reverse=True)
        return sorted_variants and sorted_variants[0]


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

class DocumentContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.DOCUMENT


class StickerContentStrategy(_DownloadableContentStrategy):
    file_extension: str = "webp"
    content_type_key: str = ContentType.STICKER
    POSSIBLE_ACTIONS = {
        MessageActions.DOWNLOAD,
        MessageActions.DOWNLOAD_ALL,
        MessageActions.DELETE_REQUEST,
    }

    @classmethod
    async def download_all(cls, msgdoc: MessageDocument, bot: Bot) -> AppResult:
        result = AppResult()
        sticker_set_name = msgdoc.sticker.set_name
        sticker_set = await bot.get_sticker_set(sticker_set_name)
        for sticker in sticker_set.stickers:
            result_ = await cls._download_file_impl(sticker, bot, dir_name=sticker_set_name)
            result.merge(result_)

        if result:
            result = cls._update_actions(msgdoc, (MessageActions.DOWNLOAD_ALL,))
        return result

    @classmethod
    def _get_extension(cls, file_data: Any) -> str:
        return "webm" if file_data.is_video else super()._get_extension(file_data)

    @staticmethod
    def _get_from_user_data(*args) -> tuple[str, str]:
        return "", ""

    @staticmethod
    def _get_from_chat_id(*args) -> tuple[str, str]:
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
    ContentType.DOCUMENT: DocumentContentStrategy,
}
