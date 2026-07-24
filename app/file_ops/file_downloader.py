import logging
import os
from typing import Mapping, ClassVar

from aiogram import Bot
from aiogram.types import ContentType

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

        from_user, _ = msgdoc.get_from_user_data()
        from_chat, _ = msgdoc.get_from_chat_data()
        await cls._download_file_impl(
            getattr(msgdoc, msgdoc.content_type),
            bot,
            from_user=from_user,
            from_chat=from_chat,
            file_extension=cls.FILE_EXTENSION_BY_CONTENT_TYPE[msgdoc.content_type],
        )

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
            file_extension = "webm" if sticker.is_video else cls.FILE_EXTENSION_BY_CONTENT_TYPE[ContentType.STICKER]
            await cls._download_file_impl(
                sticker, bot, dir_name=sticker_set_name, file_extension=file_extension
            )

    @classmethod
    async def _download_file_impl(
        cls,
        downloadable: TDownloadableVariant,
        bot: Bot,
        from_user: str | None = "",
        from_chat: str = "",
        dir_name: str = "",
        file_extension: str = "",
    ) -> None:
        if not (file_data := cls._best_quality_variant(downloadable)):
            raise FileVariantError(f"File data variant is invalid: {downloadable}")

        dir_path = os.path.join(str(from_user), dir_name)
        file_name = cls._get_file_name(file_data, from_user, from_chat, file_extension)

        await save_file(bot, file_data.file_id, file_name, dir_path)

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
    def _get_file_name(
        cls, file_data: DownloadableContentType, from_user_id: str | None, from_chat_id: str | None, file_extension: str
    ) -> str:
        file_name = f"{file_data.file_unique_id}"
        file_name = f"{file_name}.{file_extension}"
        if from_user_id and from_chat_id:
            file_name = f"{from_user_id}_{from_chat_id}-{file_name}"
        return file_name
