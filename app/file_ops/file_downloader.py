import hashlib
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import ClassVar, cast

from aiogram import Bot
from loguru import logger

from app.exceptions import InvalidMessageDocumentError
from app.models import MediaAttachment, MessageDocument
from app.models.message_media import AudioAttachment, StickerAttachment
from app.types import ContentType

from .exceptions import InvalidStickerSetError
from .ops import save_file


class FileDownloader:
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
            raise InvalidMessageDocumentError(
                f"Message document [{msgdoc.id}] has no media attachments for content type: {msgdoc.content_type}"
            )

        for media_attachment in media_attachments:
            await cls._download_file_impl(msgdoc, media_attachment, bot)

        logger.info(f"[{msgdoc.id}] File successfully downloaded.")

    @classmethod
    async def _download_stickerpack(cls, msgdoc: MessageDocument, bot: Bot) -> None:
        if not msgdoc.media or not (sticker_attachment := msgdoc.media.sticker):
            raise InvalidMessageDocumentError(detail="Message has no sticker")

        if not (sticker_set_name := sticker_attachment.set_name):
            raise InvalidStickerSetError(detail="Sticker has no set name")

        try:
            sticker_set = await bot.get_sticker_set(sticker_set_name)
        except Exception as get_sticker_set_exc:
            raise InvalidStickerSetError(
                detail=f"Error occured while getting sticker set: {sticker_set_name}"
            ) from get_sticker_set_exc

        for sticker in sticker_set.stickers:
            await cls._download_file_impl(msgdoc, cast(StickerAttachment, sticker), bot, dir_name=sticker_set_name)

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
                sticker_ext = "webm"
            else:
                sticker_ext = cls.FILE_EXTENSION_BY_CONTENT_TYPE[ContentType.STICKER]
            return f"{file_uid_hashed}.{sticker_ext}"

        ext = cls._get_file_extension(msgdoc, downloadable)

        if msgdoc.content_type == ContentType.AUDIO or isinstance(downloadable, AudioAttachment):
            if audio_file_name := cls._build_audio_file_name(msgdoc, downloadable, ext):
                return audio_file_name

        message_date = msgdoc.get_message_origin_date()
        message_source = msgdoc.get_source_data()

        return f"{message_source.source_id}_{message_date.strftime('%Y-%m-%d_%H-%M-%S')}_{file_uid_hashed}.{ext}"

    @classmethod
    def _get_file_extension(cls, msgdoc: MessageDocument, downloadable: MediaAttachment) -> str:
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

        return ext

    @staticmethod
    def _sanitize_name_component(value: str) -> str:
        sanitized = re.sub(r'[\\/:*?"<>|\0]', "_", value)
        return sanitized.strip()

    @classmethod
    def _build_audio_file_name(cls, msgdoc: MessageDocument, downloadable: MediaAttachment, ext: str) -> str | None:
        performer = getattr(downloadable, "performer", None)
        title = getattr(downloadable, "title", None)

        if not performer and not title and msgdoc.media and msgdoc.media.audio:
            performer = msgdoc.media.audio.performer
            title = msgdoc.media.audio.title

        performer = cls._sanitize_name_component(performer) if performer else None
        title = cls._sanitize_name_component(title) if title else None

        performer = performer or None
        title = title or None

        if not title and hasattr(downloadable, "file_name") and (fn := getattr(downloadable, "file_name", None)):
            fn_stem = Path(fn).stem
            title = cls._sanitize_name_component(fn_stem) or None

        if title and ext and title.lower().endswith(f".{ext.lower()}"):
            title = title[: -(len(ext) + 1)].strip() or None

        if performer and title and performer.lower() == title.lower():
            title = None

        if performer and title:
            title_lower = title.lower()
            performer_lower = performer.lower()
            if (
                title_lower.startswith(f"{performer_lower} -")
                or title_lower.startswith(f"{performer_lower} —")
                or title_lower.startswith(f"{performer_lower} –")
            ):
                stem = title
            else:
                stem = f"{performer} - {title}"
        elif performer:
            stem = performer
        elif title:
            stem = title
        else:
            return None

        return f"{stem}.{ext}"
