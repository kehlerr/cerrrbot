from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field

from app.types import ContentType


class MediaAttachment(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    file_id: str
    file_unique_id: str
    file_size: int | None = None

    _SORT_KEY: ClassVar[str | None] = None

    @classmethod
    def best_variant(cls, variants: Self | list[Self] | None) -> Self | None:
        if not isinstance(variants, list):
            return variants or None

        if len(variants) > 1 and (sort_key := variants[0]._SORT_KEY):
            return sorted(variants, key=lambda v: getattr(v, sort_key), reverse=True)[0]

        return variants[0] if variants else None


class _ShapedMediaAttachment(MediaAttachment):
    _SORT_KEY = "height"

    width: int
    height: int


class PhotoAttachment(_ShapedMediaAttachment): ...


class MediaThumbnail(PhotoAttachment): ...


class VideoAttachment(_ShapedMediaAttachment):
    duration: int
    thumbnail: MediaThumbnail | None = None
    file_name: str | None = None
    mime_type: str | None = None


class AnimationAttachment(_ShapedMediaAttachment):
    duration: int
    thumbnail: MediaThumbnail | None = None
    file_name: str | None = None
    mime_type: str | None = None


class StickerAttachment(_ShapedMediaAttachment):
    type: str = "regular"
    is_animated: bool = False
    is_video: bool = False
    thumbnail: MediaThumbnail | None = None
    emoji: str | None = None
    set_name: str | None = None


class VideoNoteAttachment(MediaAttachment):
    length: int
    duration: int
    thumbnail: MediaThumbnail | None = None


class VoiceAttachment(MediaAttachment):
    duration: int
    mime_type: str | None = None


class AudioAttachment(MediaAttachment):
    duration: int
    performer: str | None = None
    title: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    thumbnail: MediaThumbnail | None = None


class DocumentAttachment(MediaAttachment):
    thumbnail: MediaThumbnail | None = None
    file_name: str | None = None
    mime_type: str | None = None


class PollOptionInfo(BaseModel):
    text: str
    voter_count: int = 0

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class PollInfo(BaseModel):
    id: str
    question: str
    options: list[PollOptionInfo] = Field(default_factory=list)
    total_voter_count: int = 0
    is_closed: bool = False
    is_anonymous: bool = True
    type: str = "regular"
    allows_multiple_answers: bool = False

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RichMessageBlock(BaseModel):
    type: str | None = None
    blocks: list[Self] | None = None
    photo: list[PhotoAttachment] | None = None
    video: VideoAttachment | None = None
    document: DocumentAttachment | None = None
    animation: AnimationAttachment | None = None
    audio: AudioAttachment | None = None
    video_note: VideoNoteAttachment | None = None
    voice: VoiceAttachment | None = None
    sticker: StickerAttachment | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def extract_media_items(self) -> list[MediaAttachment]:
        media_items_raw: list[Any] = []

        if self.photo:
            media_items_raw.append(self.photo)
        if self.video:
            media_items_raw.append(self.video)
        if self.document:
            media_items_raw.append(self.document)
        if self.animation:
            media_items_raw.append(self.animation)
        if self.audio:
            media_items_raw.append(self.audio)
        if self.video_note:
            media_items_raw.append(self.video_note)
        if self.voice:
            media_items_raw.append(self.voice)
        if self.sticker:
            media_items_raw.append(self.sticker)

        media_items: list[MediaAttachment] = [
            attachment for attachment in (m.best_variant(m) for m in media_items_raw) if attachment is not None
        ]

        if self.blocks:
            for child in self.blocks:
                media_items.extend(child.extract_media_items())

        return media_items


class RichMessageInfo(BaseModel):
    blocks: list[RichMessageBlock] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    def extract_media_items(self) -> list[Any]:
        media_items: list[Any] = []
        for block in self.blocks:
            media_items.extend(block.extract_media_items())
        return media_items


class MessageMedia(BaseModel):
    photo: list[PhotoAttachment] | None = None
    document: DocumentAttachment | None = None
    video: VideoAttachment | None = None
    animation: AnimationAttachment | None = None
    audio: AudioAttachment | None = None
    video_note: VideoNoteAttachment | None = None
    voice: VoiceAttachment | None = None
    sticker: StickerAttachment | None = None
    rich_message: RichMessageInfo | None = None

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @classmethod
    def from_message(cls, message: Any) -> Self | None:
        raw_dump = message.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
        if hasattr(message, "rich_message") and "rich_message" not in raw_dump:
            if (rich_msg := message.rich_message) is not None:
                if isinstance(rich_msg, BaseModel):
                    raw_dump["rich_message"] = rich_msg.model_dump(by_alias=True, exclude_unset=True, exclude_none=True)
                elif isinstance(rich_msg, dict):
                    raw_dump["rich_message"] = rich_msg

        media = cls.model_validate(raw_dump)
        if not media.model_dump(exclude_none=True, exclude_unset=True):
            return None
        return media

    def get_content_attachment(self, content_type: ContentType) -> list[MediaAttachment] | MediaAttachment | None:
        if content_type == ContentType.RICH_MESSAGE_MEDIA:
            return self.rich_message.extract_media_items() if self.rich_message else None

        return MediaAttachment.best_variant(getattr(self, content_type, None))
