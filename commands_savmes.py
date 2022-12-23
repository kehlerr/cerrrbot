import logging

from typing import Optional, Any
from aiogram import Bot, types, Router, F
from aiogram.types import ContentType, CallbackQuery
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from savmes import MessageActions, ContentStrategy, perform_message_action, set_action_message_id, update_action_for_message


logger = logging.getLogger(__name__)
logger = logging.getLogger("__main__")

savmes_router = Router()

actions_by_content_type = {
        ContentType.TEXT: (MessageActions.SAVE, MessageActions.NOTE, MessageActions.TODO, MessageActions.DELETE),
        ContentType.PHOTO: (MessageActions.DOWNLOAD_FILE, MessageActions.DOWNLOAD_ALL, MessageActions.DELETE),
        ContentType.VIDEO: (MessageActions.DOWNLOAD_FILE, MessageActions.DOWNLOAD_ALL, MessageActions.DOWNLOAD_DELAY, MessageActions.DELETE),
        ContentType.ANIMATION: (MessageActions.DOWNLOAD_FILE, MessageActions.DELETE),
        ContentType.AUDIO: (MessageActions.DOWNLOAD_FILE, MessageActions.DELETE),
        ContentType.STICKER: (MessageActions.DOWNLOAD_FILE, MessageActions.DOWNLOAD_ALL, MessageActions.DELETE),
        ContentType.VIDEO_NOTE: (MessageActions.DOWNLOAD_FILE, MessageActions.DELETE),
        ContentType.VOICE: (MessageActions.DOWNLOAD_FILE, MessageActions.DELETE),
}


caption_by_action = {
    MessageActions.DELETE: "Delete",
    MessageActions.SAVE: "Save",
    MessageActions.DOWNLOAD_FILE: "Download",
    MessageActions.DOWNLOAD_ALL: "Download all",
    MessageActions.DOWNLOAD_DELAY: "Download delay",
    MessageActions.NOTE: "Note",
    MessageActions.TODO: "Note ToDo",
    MessageActions.BOOKMARK: "Add bookmark",
}

class SaveMessageData(CallbackData, prefix="savmes_menu"):
    action: MessageActions
    message_id: str
    content_type: str
    query_message: types.Message = None


EXCLUDE_MESSAGE_FIELDS = {"chat": {"first_name", "last_name"}, "from_user": {"first_name", "last_name", "language_code"}}


@savmes_router.message()
async def common_msg(message: types.Message, bot: Bot):
    message_data = message.dict(exclude_none=True, exclude_defaults=True, exclude=EXCLUDE_MESSAGE_FIELDS)
    logger.info("Received message: {}; data: {}".format(message.content_type, message_data))
    result = await ContentStrategy.add_new_message(message_data, message.content_type)
    if result and result.data.get("need_reply"):
        logger.info("Result adding: {}".format(result))
        saved_message_id = result.data["_id"]
        action_message = await message.reply(
            "Choose action for this message:",
            reply_markup=message_actions_menu_kb(saved_message_id, message.content_type)
        )
        await set_action_message_id(saved_message_id, action_message.message_id)


@savmes_router.callback_query(SaveMessageData.filter(F.action.name.in_(dir(MessageActions))))
async def on_action_pressed(query: CallbackQuery, callback_data: SaveMessageData, **kwargs):
    logger.info("Received data on chosen action: {}".format(callback_data))
    message_id = callback_data.message_id
    await update_action_for_message(message_id, callback_data.action)
    await perform_message_action(message_id, kwargs["bot"])


def message_actions_menu_kb(message_id: str, content_type: ContentType) -> types.InlineKeyboardMarkup:
    message_actions = actions_by_content_type.get(content_type, actions_by_content_type[ContentType.TEXT])

    kb_builder = InlineKeyboardBuilder()
    for action in message_actions:
        kb_builder.button(
            text=caption_by_action[action], callback_data=SaveMessageData(action=action, message_id=message_id, content_type=content_type)
        )
    return kb_builder.as_markup()
