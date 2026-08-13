from enum import StrEnum
from typing import Any, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

TPydanticModel = TypeVar("TPydanticModel", bound=BaseModel)
MessageActionCode = str


class AppBaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CERRRBOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ContentType(StrEnum):
    UNKNOWN = "unknown"
    TEXT = "text"
    PHOTO = "photo"
    STICKER = "sticker"
    VIDEO = "video"
    VIDEO_NOTE = "video_note"
    VOICE = "voice"
    HASHTAG = "hashtag"
    CASHTAG = "cashtag"
    BOT_COMMAND = "bot_command"
    MESSAGE_AUTO_DELETE_TIMER_CHANGED = "message_auto_delete_timer_changed"
    PINNED_MESSAGE = "pinned_message"
    ANIMATION = "animation"
    AUDIO = "audio"
    DOCUMENT = "document"
    STORY = "story"

    # Extended content types for rich messages
    RICH_MESSAGE_MEDIA = "rich_message_media"
    RICH_MESSAGE_TEXT = "rich_message_text"

    @classmethod
    def from_val(cls, val: Any) -> ContentType:
        if isinstance(val, cls):
            return val
        s_val = str(val.value if hasattr(val, "value") else val)
        try:
            return cls(s_val)
        except ValueError:
            return cls.UNKNOWN


class ExecutorCode(StrEnum):
    NONE = "none"
    DELETE = "delete"
    DELETE_REQUEST = "delete_request"
    DELETE_AFTER_TIME = "delete_after_time"
    NOTE_TODO = "note_todo"
    KEEP = "keep"
    DOWNLOAD = "download"
    DOWNLOAD_ALL = "download_all"
    MENU_BACK = "menu_back"
    TASK_GET_STATUS = "task_get_status"
    TASK_ABORT = "task_abort"
    CUSTOM = "custom"


class PluginStatus(StrEnum):
    LOADED = "Loaded"
    DISABLED = "Disabled"
    FAILED_LOAD = "Failed"
    NO_PLUGIN_FOUND = "No Plugin Found"


@runtime_checkable
class PydanticModelClass[TPydanticModel](Protocol):
    def model_validate(
        self,
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, Any] | None = None,
    ) -> TPydanticModel: ...

    def model_dump(
        self, *, by_alias: bool = True, exclude_unset: bool = False, exclude_defaults: bool = False, exclude_none: bool = False
    ) -> dict[str, Any]: ...
