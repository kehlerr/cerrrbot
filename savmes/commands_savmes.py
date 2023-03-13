import logging
from typing import Any, Dict

from aiogram import Bot, F, Router, types
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .constants import CUSTOM_MESSAGE_MIN_ORDER, MessageActions
from .message_document import MessageDocument
from .savmes import add_new_message, perform_message_action

logger = logging.getLogger("cerrrbot")


savmes_router = Router()


class SaveMessageData(CallbackData, prefix="SVM"):
    action: str
    message_id: str


@savmes_router.message()
async def common_msg(message: types.Message) -> None:
    logger.info("Received message: {}; data: {}".format(message.content_type, message))
    result = await add_new_message(message)
    logger.info("Result adding: {}".format(result))
    message_actions = result and result.data["message_info"].actions
    if message_actions:
        saved_message_id = result.data["_id"]
        reply_action_message = await message.reply(
            "Choose action for this message:",
            reply_markup=_build_message_actions_menu_kb(
                message_actions, saved_message_id
            ),
        )
        MessageDocument(saved_message_id).update_message_info(
            new_action=None, reply_action_message_id=reply_action_message.message_id
        )


@savmes_router.callback_query(
    SaveMessageData.filter(F.action.in_(MessageActions.CODES))
)
async def on_action_pressed(
    query: CallbackQuery, callback_data: SaveMessageData, bot: Bot
):
    logger.info("Received data on chosen action: {}".format(callback_data))
    message_id = callback_data.message_id
    msgdoc = MessageDocument(message_id)
    action_code = callback_data.action
    msgdoc.update_message_info(MessageActions.ACTION_BY_CODE[action_code])
    result = await perform_message_action(msgdoc, bot)
    if result:
        message_info = result.data.get("message_info")
        next_actions = message_info and message_info.actions
        if next_actions:
            text_result = next_actions.get(action_code, {}).get("result_info")
            if not text_result:
                next_markup = _build_message_actions_menu_kb(next_actions, message_id)
                await query.message.edit_reply_markup(next_markup)
                return
        else:
            text_result = "Superb done, Your Majesty!"
    else:
        text_result = """
            Regret to infrom, that some error/exception occured.\n
            Please, check logs for more information
        """

    await query.answer(text_result)


def _build_message_actions_menu_kb(
    actions_data: Dict[str, Any], message_id: str
) -> types.InlineKeyboardMarkup:
    message_actions = sorted(
        [MessageActions.ACTION_BY_CODE[action] for action in actions_data]
    )
    kb_builder = InlineKeyboardBuilder()
    actions_buttons = []
    custom_actions_buttons = []
    for action in message_actions:
        additional_caption = actions_data[action.code].get("additional_caption", "")
        button = InlineKeyboardButton(
            text=f"{action.caption}{additional_caption}",
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
