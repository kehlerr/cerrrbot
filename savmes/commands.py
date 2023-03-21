import logging
from typing import Any, Dict, List

from aiogram import Bot, F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .api import add_new_message, perform_message_action
from .common import MessageActions, MessageAction
from .constants import CUSTOM_MESSAGE_MIN_ORDER
from .message_document import MessageDocument

logger = logging.getLogger("cerrrbot")


savmes_router = Router()


class SaveMessageData(CallbackData, prefix="SVM"):
    action: str
    message_id: str


@savmes_router.message()
async def on_received_new_common_message(message: Message) -> None:
    logger.info(f"Received message: {message}")
    result = await add_new_message(message)
    if result:
        await _process_received_message(message, result.data)
    else:
        logger.warning(f"Result adding: {result}")


async def _process_received_message(
    message: Message, result_data: Dict[str, Any]
) -> None:
    message_actions = result_data["reply_info"].actions
    if not message_actions:
        return

    saved_message_id = result_data["_id"]
    reply_action_message = await message.reply(
        "Choose action for this message:",
        reply_markup=_build_message_actions_menu_kb(message_actions, saved_message_id),
    )
    MessageDocument(saved_message_id).update_message_info(
        new_action=None, reply_action_message_id=reply_action_message.message_id
    )


@savmes_router.callback_query(SaveMessageData.filter(F.action.in_(MessageActions.CODES)))
async def on_action_pressed(
    query: CallbackQuery, callback_data: SaveMessageData, bot: Bot
) -> None:
    logger.info("Received data on chosen action: {}".format(callback_data))
    message_id = callback_data.message_id
    result = await perform_message_action(message_id, bot, callback_data.action)
    if not result:
        await query.answer("Some error/exception occured, check logs for details.")
        return

    await _process_pressed_action_result(query, message_id, result.data["reply_info"])


async def _process_pressed_action_result(
    query: CallbackQuery, message_id: str, reply_info: Dict[str, Any]
) -> None:
    try:
        if reply_info.popup_text:
            await query.answer(reply_info.popup_text)
            if not reply_info.need_edit_buttons:
                return
    except (AttributeError, KeyError):
        pass

    if not reply_info.actions:
        await query.answer()
        return

    next_markup = _build_message_actions_menu_kb(reply_info.actions, message_id)
    await query.message.edit_reply_markup(next_markup)


def _build_message_actions_menu_kb(
    reply_actions: List[MessageAction], message_id: str
) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    actions_buttons = []
    custom_actions_buttons = []
    for action in reply_actions:
        button = InlineKeyboardButton(
            text=action.caption,
            callback_data=SaveMessageData(
                action=action.code,
                message_id=message_id,
            ).pack(),
        )
        if action.order >= CUSTOM_MESSAGE_MIN_ORDER:
            custom_actions_buttons.append(button)
        else:
            actions_buttons.append(button)
    kb_builder.row(*actions_buttons)
    kb_builder.row(*custom_actions_buttons)

    return kb_builder.as_markup()
