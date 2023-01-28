import logging
from typing import List

from aiogram import Bot, F, Router, types
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .constants import MessageAction, MessageActions
from .message_document import MessageDocument
from .savmes import add_new_message, perform_message_action

logger = logging.getLogger("cerrrbot")


savmes_router = Router()


class SaveMessageData(CallbackData, prefix="SVM"):
    action: str
    message_id: str
    content_type: str


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
                message_actions, saved_message_id, message.content_type
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
    msgdoc.update_message_info(MessageActions.ACTION_BY_CODE[callback_data.action])
    result = await perform_message_action(msgdoc, bot)
    text_result = ""
    if result:
        message_info = result.data.get("message_info")
        next_actions = message_info and message_info.actions
        if next_actions:
            next_markup = _build_message_actions_menu_kb(
                next_actions, message_id, msgdoc.content_type
            )
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
