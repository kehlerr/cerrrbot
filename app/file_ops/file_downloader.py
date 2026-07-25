import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Mapping, ClassVar, cast

from aiogram import Bot

from aiogram.types import ContentType, Sticker

from app.exceptions import InvalidMessageDocumentError
from app.models import MessageDocument
from app.types import DownloadableContentType, TDownloadableVariant

from .exceptions import FileVariantError, InvalidStickerSetError
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

        await cls._download_file_impl(msgdoc, getattr(msgdoc, msgdoc.content_type), bot)

        logger.info(f"[{msgdoc.id}] File successfully downloaded.")

    @classmethod
    async def _download_stickerpack(cls, msgdoc: MessageDocument, bot: Bot) -> None:
        if not msgdoc.sticker:
            raise InvalidMessageDocumentError(detail="Message has no sticker")

        if not (sticker_set_name := msgdoc.sticker.set_name):
            raise InvalidStickerSetError(detail="Sticker has no set name")

        try:
            sticker_set = await bot.get_sticker_set(sticker_set_name)
        except Exception as get_sticker_set_exc:
            raise InvalidStickerSetError(detail=f"Error occured while getting sticker set: {sticker_set_name}") from get_sticker_set_exc

        for sticker in sticker_set.stickers:
            await cls._download_file_impl(msgdoc, sticker, bot, dir_name=sticker_set_name)

    @classmethod
    async def _download_file_impl(
        cls,
        msgdoc: MessageDocument,
        downloadable: TDownloadableVariant,
        bot: Bot,
        dir_name: str | None = None,
    ) -> None:
        if not (file_data := cls._best_quality_variant(downloadable)):
            raise FileVariantError(f"File data variant is invalid: {downloadable}")

        if not dir_name:
            dir_name = datetime.now().strftime("%Y-%m")

        file_name = cls._build_file_name(msgdoc, file_data, downloadable)

        await save_file(bot, file_data.file_id, file_name, dir_name)

    @classmethod
    def _best_quality_variant(cls, downloadable_variant: TDownloadableVariant) -> DownloadableContentType | None:

        if not isinstance(downloadable_variant, list):
            return downloadable_variant or None

        if len(downloadable_variant) > 1:
            return sorted(
                downloadable_variant, key=lambda v: getattr(v, cls.SORT_KEY), reverse=True
            )[0]
        else:
            return downloadable_variant[0] if downloadable_variant else None

    @classmethod
    def _build_file_name(cls, msgdoc: MessageDocument, file_data: DownloadableContentType, downloadable: TDownloadableVariant) -> str:

        file_uid_hashed = hashlib.sha256(file_data.file_unique_id.encode()).hexdigest()[:8]

        if msgdoc.content_type == ContentType.STICKER:
            downloadable = cast(Sticker, downloadable)
            if downloadable.is_animated or downloadable.is_video:
                ext = "webm"
            else:
                ext = cls.FILE_EXTENSION_BY_CONTENT_TYPE[ContentType.STICKER]
            return f"{file_uid_hashed}.{ext}"

        if forward_origin := msgdoc.forward_origin:
            message_date = forward_origin.date
        else:
            message_date = msgdoc.date

        ext = None
        if hasattr(file_data, "file_name") and (file_name := file_data.file_name):  # type: ignore[attr-defined]
            if suffix := Path(file_name).suffix.lstrip("."):
                ext = suffix.lower()

        if not ext:
            ext = cls.FILE_EXTENSION_BY_CONTENT_TYPE.get(msgdoc.content_type, "bin")

        return f"{msgdoc.get_message_source()}_{message_date.strftime('%Y-%m-%d_%H-%M-%S')}_{file_uid_hashed}.{ext}"