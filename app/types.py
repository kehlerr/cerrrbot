from enum import StrEnum
from typing import Any, TypeVar, Protocol, runtime_checkable

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    PhotoSize,
    Video,
    VideoNote,
    Document,
    Sticker,
    Audio,
    Animation,
    VideoQuality,
)
from pydantic import BaseModel


DownloadableContentType = PhotoSize | Video | VideoNote | Document | Sticker | Audio | Animation | VideoQuality

TDownloadableVariant = DownloadableContentType | list[DownloadableContentType]

TPydanticModel = TypeVar("TPydanticModel", bound=BaseModel)


MessageActionCode = str

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



@runtime_checkable
class PydanticModelClass[TPydanticModel](Protocol):
    def model_validate(
        self,
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, Any] | None = None
    ) -> TPydanticModel:
        ...

    def model_dump(
        self,
        *,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> dict[str, Any]:
        ...


class ActionCallbackData(CallbackData, prefix="SVM"):
    action: str
    msgdoc_id: str
