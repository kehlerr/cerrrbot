import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from constants import (
    DEFAULT_PAGE_LIMIT,
    DEFAULT_TIMEOUT_TO_DELETE_MESSAGES,
    Action,
    UserAction,
)
from keyboards import Keyboards as kbs
from settings import ALLOWED_USERS, DATA_DIRECTORY_ROOT


logger = logging.getLogger("cerrrbot")


@dataclass
class ContentData:
    data: dict
    page_limit: int = DEFAULT_PAGE_LIMIT


@dataclass
class AppResult:
    status: Union[int, bool] = True
    info: Optional[str] = ""
    _info: list[str] = field(default_factory=lambda: [])
    data: dict[Any] = field(default_factory=lambda: {})

    def __bool__(self) -> bool:
        return self.status

    def __str__(self) -> str:
        _str = f"Result:{self.status}; {self.info}"
        if self._info:
            _str += "\n".join(self._info)
        return _str

    def merge(self, *other_results) -> None:
        for result in other_results:
            if not result.status:
                self.status = result.status
                self._info.append(str(result.info))
                self.data.update(result.data)


async def navigate_content(query, callback_data: UserAction, state: FSMContext):
    direction = 1 if callback_data.action == Action.nav_next else -1
    await show_nav_content(query.message, state, direction)


async def show_nav_content(message: Message, state: FSMContext, direction: int = 0):
    state_data = await state.get_data()
    content = state_data.get("content_data")
    if not content or not content.data:
        return

    content_size = len(content.data)

    content_limit = content.page_limit
    nav_idx = state_data.get("nav_idx", 0)
    nav_idx += direction * content_limit
    if nav_idx < 0 or nav_idx > content_size:
        return

    reply_markup = None
    if content_size < content_limit:
        reply_markup = kbs.back_to_main_menu
    else:
        if nav_idx - content_limit < 0:
            reply_markup = kbs.nav_menu_without_prev

        if nav_idx + content_limit >= content_size:
            reply_markup = kbs.nav_menu_without_next

        await state.update_data(nav_idx=nav_idx)

    data_part = content.data[nav_idx : nav_idx + content_limit]
    answer_text = "\n".join(data_part)

    reply_markup = reply_markup or kbs.nav_menu
    if direction == 0 and nav_idx == 0:
        await message.answer(answer_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await message.edit_text(
            answer_text, reply_markup=reply_markup, parse_mode="HTML"
        )


class CheckUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        message: Message,
        data: Dict[str, Any],
    ) -> Any:
        user_sender = message.from_user
        if user_sender.id in ALLOWED_USERS:
            return await handler(message, data)

        logger.warning(
            "Someone tried to send message;\nUser: {};\nMessage: {}".format(
                user_sender, message
            )
        )


async def delete_messages_after_timeout(
    messages: List[Message], timeout=DEFAULT_TIMEOUT_TO_DELETE_MESSAGES
):
    if timeout > 0:
        await asyncio.sleep(timeout)

    for message in messages:
        await message.delete()


def create_directory(directory_name: str) -> AppResult:
    directory_path = get_directory_path(directory_name)
    try:
        os.mkdir(directory_path)
    except Exception as exc:
        result = AppResult(False, exc)
    else:
        result = AppResult(True, data=directory_path)

    return result


def get_directory_path(directory_path: str) -> os.PathLike:
    return os.path.join(DATA_DIRECTORY_ROOT, directory_path)
