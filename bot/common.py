import logging
import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message
from settings import ALLOWED_USERS, DATA_DIRECTORY_ROOT

logger = logging.getLogger("cerrrbot")


@dataclass
class AppResult:
    status: int | bool = True
    info: Optional[str] = ""
    _info: list[str] = field(default_factory=lambda: [])
    data: dict[Any] = field(default_factory=lambda: {})

    def __bool__(self) -> bool:
        return self.status

    def __getattr__(self, __name: str) -> Any:
        return self.data[__name]

    def __json__(self):
        return self.data

    def __str__(self) -> str:
        _str = f"Result:{self.status}; {self.info}"
        if self._info:
            _str += "\n".join(self._info)
        if self.data:
            _str = f"\nData:{self.data}"
        return _str

    def merge(self, *other_results) -> None:
        for result in other_results:
            if isinstance(result, bool):
                self.status = self.status and result
                continue

            self._merge_another(result)

    def _merge_another(self, app_result):
        self.status = self.status and app_result.status
        self._info.extend(str(app_result._info))
        self.data.update(app_result.data)


class CheckUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        message: Message,
        data: dict[str, Any],
    ) -> Any:
        user_sender = message.from_user
        if user_sender.id in ALLOWED_USERS:
            return await handler(message, data)

        logger.warning(
            "Someone tried to send message;\nUser: {};\nMessage: {}".format(
                user_sender, message
            )
        )


def create_directory(directory_name: str) -> AppResult:
    directory_path = get_directory_path(directory_name)

    if os.path.exists(directory_path):
        return AppResult(True, data={"path": directory_path})

    try:
        os.mkdir(directory_path)
    except Exception as exc:
        result = AppResult(False, exc)
    else:
        result = AppResult(True, data={"path": directory_path})

    return result


def get_directory_path(directory_path: str) -> os.PathLike:
    return os.path.join(DATA_DIRECTORY_ROOT, directory_path)


async def save_file(bot: Bot, file_id: str, file_name: str, dir_name: str) -> AppResult:
    dir_path = os.path.join(DATA_DIRECTORY_ROOT, dir_name)
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)

    file_path = os.path.join(dir_path, file_name)
    try:
        await bot.download(file_id, file_path)
    except Exception as exc:
        logger.error(exc)
        return AppResult(False, exc)

    return AppResult()