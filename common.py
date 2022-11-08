import asyncio
from dataclasses import dataclass
from typing import Optional, Union, List
from enum import Enum

from aiogram import types
from aiogram.filters import callback_data
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder


class Action(str, Enum):
    cancel = "CANCEL"
    nav_prev = "NAV_PREV"
    nav_next = "NAV_NEXT"
    edit_overwrite = "EDIT_OVERWRITE"
    edit_append = "EDIT_APPEND"


class UserAction(callback_data.CallbackData, prefix="user"):
    action: Action


@dataclass
class ContentData:
    data: dict
    page_limit: int = 10


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
        reply_markup = back_to_main_menu_kb()
    else:
        if nav_idx - content_limit < 0:
            reply_markup = nav_menu_without_prev_kb()

        if nav_idx + content_limit >= content_size:
            reply_markup = nav_menu_without_next_kb()

        await state.update_data(nav_idx=nav_idx)

    data_part = content.data[nav_idx:nav_idx+content_limit]
    answer_text = "\n".join(data_part)

    reply_markup = reply_markup or nav_menu_kb()
    if direction == 0 and nav_idx == 0:
        await message.answer(answer_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await message.edit_text(answer_text, reply_markup=reply_markup, parse_mode="HTML")


def back_to_main_menu_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))

    return kb_builder.as_markup()


def pass_edit_menu_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Append", callback_data=UserAction(action=Action.edit_append))
    kb_builder.button(text="Owerwrite", callback_data=UserAction(action=Action.edit_overwrite))
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))

    return kb_builder.as_markup()


def nav_menu_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="<-", callback_data=UserAction(action=Action.nav_prev))
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))
    kb_builder.button(text="->", callback_data=UserAction(action=Action.nav_next))

    return kb_builder.as_markup()


def nav_menu_without_next_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="<-", callback_data=UserAction(action=Action.nav_prev))
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))

    return kb_builder.as_markup()


def nav_menu_without_prev_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))
    kb_builder.button(text="->", callback_data=UserAction(action=Action.nav_next))

    return kb_builder.as_markup()


async def delete_messages_after_timeout(messages: List[types.Message], timeout=15):
    await asyncio.sleep(timeout)
    for message in messages:
        await message.delete()
