from typing import Mapping

from app import app_settings

from app.actions import MessageActions
from app.models import ActionsData, MessageAction, MessageDocument, PreparedMessageInfo
from app.types import ContentType

from .message_parser import MessageParser


class ContentStrategyBase:
    DEFAULT_MESSAGE_TTL = app_settings.timeout_before_default_action_performs
    DEFAULT_ACTION = MessageActions.DELETE_1

    POSSIBLE_ACTIONS = {
        MessageActions.KEEP,
        MessageActions.DELETE_REQUEST,
    }

    @classmethod
    def process_new_msgdoc(cls, msgdoc: MessageDocument) -> MessageDocument:
        prepared_message_info = cls.prepare_message_info(msgdoc)
        msgdoc.set_message_info(prepared_message_info)
        return msgdoc


    @classmethod
    def prepare_message_info(cls, msgdoc: MessageDocument) -> PreparedMessageInfo:

        if msgdoc.is_subsequent_in_media_group:
            actions_menu: dict[MessageAction, ActionsData] = {}
        else:
            actions_menu = {action: {} for action in cls.POSSIBLE_ACTIONS}

        if parsed_actions := cls._parse_custom_actions(msgdoc):
            actions_menu.update(parsed_actions)

        return PreparedMessageInfo(
            action=cls.DEFAULT_ACTION,
            actions_menu=actions_menu,
            ttl=cls.DEFAULT_MESSAGE_TTL
        )

    @classmethod
    def _parse_custom_actions(cls, msgdoc: MessageDocument) -> dict[MessageAction, ActionsData]:
        message_text = msgdoc.caption or msgdoc.text
        parser = MessageParser(message_text, msgdoc.entities)
        parser.parse()
        return parser.actions


class ContentStrategy(ContentStrategyBase):
    ...

class CustomizableContentStrategy(ContentStrategy):
    ...


class _DownloadableContentStrategy(ContentStrategy):
    content_type_key: str

    DEFAULT_ACTION = MessageActions.KEEP
    POSSIBLE_ACTIONS = {
        MessageActions.KEEP,
        MessageActions.DELETE_REQUEST,
        MessageActions.DOWNLOAD,
    }

    @classmethod
    def prepare_message_info(cls, msgdoc: MessageDocument) -> PreparedMessageInfo:
        message_info = super().prepare_message_info(msgdoc)
        message_actions = message_info.actions_menu

        target_attr = getattr(msgdoc, cls.content_type_key, None)
        fsize: int = 0
        if (
            cls.content_type_key == ContentType.PHOTO
            or cls.content_type_key == ContentType.RICH_MESSAGE_MEDIA
        ):
            fsize = 0
        elif target_attr and hasattr(target_attr, "file_size"):
            fsize = getattr(target_attr, "file_size") or 0

        if app_settings.max_load_file_size < 0 or fsize < app_settings.max_load_file_size:
            message_info.action = MessageActions.DOWNLOAD
            if message_actions and msgdoc.media_group_id:
                message_actions.pop(MessageActions.DOWNLOAD, None)
                message_actions[MessageActions.DOWNLOAD_ALL] = {}
        else:
            message_actions.pop(MessageActions.DOWNLOAD, None)
        return message_info


class PhotoContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.PHOTO


class VideoContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.VIDEO


class AnimationContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.ANIMATION


class AudioContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.AUDIO


class VideonoteContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.VIDEO_NOTE


class VoiceContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.VOICE


class DocumentContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.DOCUMENT


class StickerContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.STICKER
    POSSIBLE_ACTIONS = {
        MessageActions.DOWNLOAD,
        MessageActions.DOWNLOAD_ALL,
        MessageActions.DELETE_REQUEST,
    }


class RichMessageMediaContentStrategy(_DownloadableContentStrategy):
    content_type_key: str = ContentType.RICH_MESSAGE_MEDIA


cls_strategy_by_content_type: Mapping[str | ContentType, type[ContentStrategy]] = {
    ContentType.TEXT: ContentStrategy,
    ContentType.PHOTO: PhotoContentStrategy,
    ContentType.VIDEO: VideoContentStrategy,
    ContentType.ANIMATION: AnimationContentStrategy,
    ContentType.AUDIO: AudioContentStrategy,
    ContentType.STICKER: StickerContentStrategy,
    ContentType.VIDEO_NOTE: VideonoteContentStrategy,
    ContentType.VOICE: VoiceContentStrategy,
    ContentType.DOCUMENT: DocumentContentStrategy,
    ContentType.RICH_MESSAGE_MEDIA: RichMessageMediaContentStrategy,
    ContentType.RICH_MESSAGE_TEXT: ContentStrategy,
}
