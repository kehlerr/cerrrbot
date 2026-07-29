import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Mapping, ClassVar, cast

from aiogram import Bot

from app.exceptions import InvalidMessageDocumentError
from app.models import MessageDocument, MediaAttachment
from app.models.message_media import StickerAttachment
from app.types import ContentType

from .exceptions import InvalidStickerSetError
from .ops import save_file

logger = logging.getLogger("cerrrbot")


class FileDownloader:

    SORT_KEY: str = "height"
    FILE_EXTENSION_BY_CONTENT_TYPE: ClassVar[Mapping[str | ContentType, str]] = {
        ContentType.PHOTO: "jpg",
        ContentType.DOCUMENT: "pdf",
        ContentType.VIDEO: "mp4",
        ContentType.ANIMATION: "mp4",
        ContentType.AUDIO: "mp3",
        ContentType.VIDEO_NOTE: "mp4",
        ContentType.VOICE: "ogg",
        ContentType.STICKER: "webp",
    }


    @classmethod
    async def download_one(cls, msgdoc: MessageDocument, bot: Bot) -> None:
        await cls._download(msgdoc, bot)

    @classmethod
    async def download_many(cls, msgdocs: list[MessageDocument], bot: Bot) -> None:
        if not msgdocs:
            logger.warning("No messages to download")
            return

        if msgdocs[0].content_type == ContentType.STICKER:
            await cls._download_stickerpack(msgdocs[0], bot)
            return

        for msgdoc in msgdocs:
            await cls._download(msgdoc, bot)

    @classmethod
    async def _download(cls, msgdoc: MessageDocument, bot: Bot) -> None:
        logger.info(f"[{msgdoc.id}] Start downloading file...")

        if not (media_attachments := msgdoc.get_media_attachments(msgdoc.content_type)):
            raise # TODO: proper exception

        for media_attachment in media_attachments:
            await cls._download_file_impl(msgdoc, media_attachment, bot)

        logger.info(f"[{msgdoc.id}] File successfully downloaded.")

    @classmethod
    async def _download_stickerpack(cls, msgdoc: MessageDocument, bot: Bot) -> None:
        if not msgdoc.media or not (sticker := msgdoc.media.sticker):
            raise InvalidMessageDocumentError(detail="Message has no sticker")

        if not (sticker_set_name := sticker.set_name):
            raise InvalidStickerSetError(detail="Sticker has no set name")

        try:
            sticker_set = await bot.get_sticker_set(sticker_set_name)
        except Exception as get_sticker_set_exc:
            raise InvalidStickerSetError(
                detail=f"Error occured while getting sticker set: {sticker_set_name}"
            ) from get_sticker_set_exc

        for sticker in sticker_set.stickers:
            await cls._download_file_impl(msgdoc, cast(MediaAttachment, sticker), bot, dir_name=sticker_set_name)

    @classmethod
    async def _download_file_impl(
        cls,
        msgdoc: MessageDocument,
        media_attachment: MediaAttachment,
        bot: Bot,
        dir_name: str | None = None,
    ) -> None:
        if not dir_name:
            dir_name = datetime.now().strftime("%Y-%m")

        file_name = cls._build_file_name(msgdoc, media_attachment)

        await save_file(bot, media_attachment.file_id, file_name, dir_name)

    @classmethod
    def _build_file_name(cls, msgdoc: MessageDocument, downloadable: MediaAttachment) -> str:

        file_uid_hashed = hashlib.sha256(downloadable.file_unique_id.encode()).hexdigest()[:8]

        if msgdoc.content_type == ContentType.STICKER:
            downloadable = cast(StickerAttachment, downloadable)
            if downloadable.is_animated or downloadable.is_video:
                ext = "webm"
            else:
                ext = cls.FILE_EXTENSION_BY_CONTENT_TYPE[ContentType.STICKER]
            return f"{file_uid_hashed}.{ext}"

        message_date = msgdoc.get_message_origin_date()

        ext = None
        if hasattr(downloadable, "file_name") and (file_name := getattr(downloadable, "file_name", None)):
            if suffix := Path(file_name).suffix.lstrip("."):
                ext = suffix.lower()

        if not ext:
            type_name = type(downloadable).__name__
            if "Photo" in type_name:
                ext = "jpg"
            elif "VideoNote" in type_name:
                ext = "mp4"
            elif "Video" in type_name:
                ext = "mp4"
            elif "Animation" in type_name:
                ext = "mp4"
            elif "Audio" in type_name:
                ext = "mp3"
            elif "Voice" in type_name:
                ext = "ogg"
            elif "Sticker" in type_name:
                ext = "webp"
            elif hasattr(downloadable, "mime_type") and (mime := getattr(downloadable, "mime_type", None)):
                import mimetypes
                if guessed := mimetypes.guess_extension(mime):
                    ext = guessed.lstrip(".").lower()

        if not ext:
            ext = cls.FILE_EXTENSION_BY_CONTENT_TYPE.get(msgdoc.content_type, "bin")

        message_source = msgdoc.get_source_data()

        return f"{message_source.source_id}_{message_date.strftime('%Y-%m-%d_%H-%M-%S')}_{file_uid_hashed}.{ext}"