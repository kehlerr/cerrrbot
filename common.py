import asyncio
from dataclasses import dataclass
from typing import Optional, Union, List

from aiogram import types
from aiogram.fsm.context import FSMContext

from constants import Action, UserAction, DEFAULT_PAGE_LIMIT, DEFAULT_TIMEOUT_TO_DELETE_MESSAGES
from keyboards import Keyboards as kbs


@dataclass
class ContentData:
    data: dict
    page_limit: int = DEFAULT_PAGE_LIMIT


@dataclass
class AppResponse:
    status: Union[int, bool]
    result_info: Optional[str] = ""


async def navigate_content(query, callback_data: UserAction, state: FSMContext):
    direction = 1 if callback_data.action == Action.nav_next else -1
    await show_nav_content(query.message, state, direction)


async def show_nav_content(message: types.Message, state: FSMContext, direction: int = 0):
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

    data_part = content.data[nav_idx:nav_idx+content_limit]
    answer_text = "\n".join(data_part)

    reply_markup = reply_markup or kbs.nav_menu
    if direction == 0 and nav_idx == 0:
        await message.answer(answer_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await message.edit_text(answer_text, reply_markup=reply_markup, parse_mode="HTML")


async def delete_messages_after_timeout(messages: List[types.Message], timeout=DEFAULT_TIMEOUT_TO_DELETE_MESSAGES):
    if timeout > 0:
        await asyncio.sleep(timeout)

    for message in messages:
        await message.delete()
