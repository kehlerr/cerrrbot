import logging
from typing import List

from aiogram import Bot, F, Router, types
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .savmes import (MessageAction, MessageActions, add_new_message,
                     perform_message_action, set_action_message_id,
                     update_action_for_message)

logger = logging.getLogger("cerrrbot")


savmes_router = Router()


class SaveMessageData(CallbackData, prefix="SVM"):
    action: str
    message_id: str
    content_type: str


@savmes_router.message()
async def common_msg(message: types.Message, bot: Bot):
    logger.info(
        "Received message: {}; data: {}".format(message.content_type, message)
    )
    result = await add_new_message(message)
    if result and result.data.get("need_reply"):
        logger.info("Result adding: {}".format(result))
        saved_message_id = result.data["_id"]
        message_actions = result.data["next_actions"]
        action_message = await message.reply(
            "Choose action for this message:",
            reply_markup=_build_message_actions_menu_kb(
                message_actions, saved_message_id, message.content_type
            ),
        )
        await set_action_message_id(saved_message_id, action_message.message_id)


@savmes_router.callback_query(
    SaveMessageData.filter(F.action.in_(MessageActions.CODES))
)
async def on_action_pressed(
    query: CallbackQuery, callback_data: SaveMessageData, bot: Bot, **kwargs
):
    logger.info("Received data on chosen action: {}".format(callback_data))
    message_id = callback_data.message_id
    await update_action_for_message(message_id, MessageActions.ACTION_BY_CODE[callback_data.action])
    result = await perform_message_action(message_id, bot)
    if result:
        text_result = ""
        next_actions = (
            isinstance(result.data, dict) and result.data.get("next_actions") or None
        )
        if next_actions:
            next_markup = _build_message_actions_menu_kb(
                next_actions, message_id, callback_data.content_type
            )
            await query.message.edit_reply_markup(next_markup)
        else:
            text_result = "Superb done, Your Majesty!"
    else:
        text_result = "Regret to infrom, that some error/exception occured.\n Please, check logs for more information"

    await query.answer(text_result)


def _build_message_actions_menu_kb(
    actions: List[MessageAction], message_id: str, content_type: str
) -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for action in sorted(actions):
        kb_builder.button(
            text=action.caption,
            callback_data=SaveMessageData(
                action=action.code, message_id=message_id, content_type=content_type
            ),
        )
    return kb_builder.as_markup()
