import logging
from typing import Any, Dict, List, Optional

from aiogram import Bot, F, Router
from aiogram.methods import EditMessageReplyMarkup
from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .actions import MessageAction, MessageActions
from .api import add_new_message, get_messages_to_perform_actions, perform_message_action
from .constants import CUSTOM_MESSAGE_MIN_ORDER
from .message_document import MessageDocument
from common import AppExceptionError

logger = logging.getLogger("cerrrbot")


router = Router()


class SaveMessageData(CallbackData, prefix="SVM"):
    action: str
    msgdoc_id: str


@router.message()
async def on_received_message(message: Message) -> None:
    logger.debug(f"Received new message: {message}")
    result = await add_new_message(message)
    if result:
        await _process_received_message(message, result.data)
    else:
        logger.warning(f"Result adding: {result}")


async def _process_received_message(
    message: Message, result_data: Dict[str, Any]
) -> None:
    try:
        message_actions = result_data["reply_info"].actions
    except KeyError:
        message_actions = None

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


@router.callback_query(SaveMessageData.filter(F.action.in_(MessageActions.CODES)))
async def on_action_pressed(
    query: CallbackQuery, callback_data: SaveMessageData, bot: Bot
) -> None:
    logger.info("Received data on chosen action: {}".format(callback_data))
    msgdoc_id = callback_data.msgdoc_id
    result = await perform_message_action(msgdoc_id, bot, callback_data.action)
    if not result:
        await query.answer("Some error/exception occured, check logs for details.")
        return

    await process_performed_action_result(msgdoc_id, result, query=query)


async def perform_message_actions(bot: Bot) -> None:
    messages = await get_messages_to_perform_actions(bot)
    for msgdoc in messages:
        msgdoc_id = str(msgdoc["_id"])
        # MessageDocument(msgdoc_id).delete()
        # continue
        result = await perform_message_action(msgdoc_id, bot)
        if result:
            await process_performed_action_result(msgdoc_id, result, bot=bot, chat_id=msgdoc["chat"]["id"])


async def process_performed_action_result(
    msgdoc_id: str, result: Dict[str, Any],
    query: Optional[CallbackQuery] = None,
    bot: Optional[Bot] = None, chat_id: Optional[int] = None
) -> None:

    try:
        reply_info = result.data["reply_info"]
    except (AttributeError, KeyError):
        reply_info = None
        pass

    if not (reply_info and reply_info.actions):
        return

    next_markup = _build_message_actions_menu_kb(reply_info.actions, msgdoc_id)

    if query:
        if reply_info.popup_text:
            await query.answer(reply_info.popup_text)
        if reply_info.need_edit_buttons:
            await query.message.edit_reply_markup(next_markup)
        return

    if not reply_info.reply_action_message_id or not reply_info.need_edit_buttons:
        return
    await bot.edit_message_reply_markup(chat_id, reply_info.reply_action_message_id, reply_markup=next_markup)


def _build_message_actions_menu_kb(
    reply_actions: List[MessageAction], msgdoc_id: str
) -> InlineKeyboardMarkup:

    kb_builder = InlineKeyboardBuilder()
    actions_buttons = []
    custom_actions_buttons = {}
    for action in reply_actions:
        button = InlineKeyboardButton(
            text=action.caption,
            callback_data=SaveMessageData(
                action=action.code,
                msgdoc_id=msgdoc_id,
            ).pack(),
        )
        if action.order >= CUSTOM_MESSAGE_MIN_ORDER:
            custom_actions_buttons.setdefault(action.order // 100, []).append(button)
        else:
            actions_buttons.append(button)
    kb_builder.row(*actions_buttons)
    for buttons in custom_actions_buttons.values():
        kb_builder.row(*buttons)

    return kb_builder.as_markup()
