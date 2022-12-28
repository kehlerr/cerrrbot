import logging

from aiogram import Bot, F, Router, types
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, ContentType
from aiogram.utils.keyboard import InlineKeyboardBuilder

from savmes import (
    ContentStrategy,
    MessageActions,
    perform_message_action,
    set_action_message_id,
    update_action_for_message,
)

logger = logging.getLogger("cerrrbot")


savmes_router = Router()

actions_by_content_type = {
    ContentType.TEXT: (
        MessageActions.SAVE,
        MessageActions.NOTE,
        MessageActions.DELETE_REQUEST,
    ),
    ContentType.PHOTO: (
        MessageActions.DOWNLOAD_FILE,
        MessageActions.DOWNLOAD_ALL,
        MessageActions.DELETE_REQUEST,
    ),
    ContentType.VIDEO: (
        MessageActions.DOWNLOAD_FILE,
        MessageActions.DOWNLOAD_ALL,
        MessageActions.DOWNLOAD_DELAY,
        MessageActions.DELETE_REQUEST,
    ),
    ContentType.ANIMATION: (
        MessageActions.DOWNLOAD_FILE,
        MessageActions.DELETE_REQUEST,
    ),
    ContentType.STICKER: (
        MessageActions.DOWNLOAD_FILE,
        MessageActions.DOWNLOAD_ALL,
        MessageActions.DELETE_REQUEST,
    ),
    ContentType.AUDIO: (MessageActions.DOWNLOAD_FILE, MessageActions.DELETE_REQUEST),
    ContentType.VOICE: (MessageActions.DOWNLOAD_FILE, MessageActions.DELETE_REQUEST),
    ContentType.VIDEO_NOTE: (
        MessageActions.DOWNLOAD_FILE,
        MessageActions.DELETE_REQUEST,
    ),
}


caption_by_action = {
    MessageActions.DELETE_REQUEST: "Delete",
    MessageActions.DELETE_NOW: "Del now",
    MessageActions.DELETE_1: "Del in 15m",
    MessageActions.DELETE_2: "Del in 12H",
    MessageActions.DELETE_3: "Del in 48H",
    MessageActions.DELETE_FROM_CHAT: "Del from chat",
    MessageActions.SAVE: "Save",
    MessageActions.DOWNLOAD_FILE: "Download",
    MessageActions.DOWNLOAD_ALL: "Download all",
    MessageActions.DOWNLOAD_DELAY: "Download delay",
    MessageActions.NOTE: "Note",
    MessageActions.TODO: "Note ToDo",
    MessageActions.BOOKMARK: "Add bookmark",
}


class SaveMessageData(CallbackData, prefix="SVM"):
    action: MessageActions
    message_id: str
    content_type: str


EXCLUDE_MESSAGE_FIELDS = {
    "chat": {"first_name", "last_name"},
    "from_user": {"first_name", "last_name", "language_code"},
}


@savmes_router.message()
async def common_msg(message: types.Message, bot: Bot):
    print(message)
    message_data = message.dict(
        exclude_none=True, exclude_defaults=True, exclude=EXCLUDE_MESSAGE_FIELDS
    )
    logger.info(
        "Received message: {}; data: {}".format(message.content_type, message_data)
    )
    result = await ContentStrategy.add_new_message(message_data, message.content_type)
    if result and result.data.get("need_reply"):
        logger.info("Result adding: {}".format(result))
        saved_message_id = result.data["_id"]
        action_message = await message.reply(
            "Choose action for this message:",
            reply_markup=actions_menu_by_content_type_kb(
                saved_message_id, message.content_type
            ),
        )
        await set_action_message_id(saved_message_id, action_message.message_id)


@savmes_router.callback_query(
    SaveMessageData.filter(F.action.name.in_(dir(MessageActions)))
)
async def on_action_pressed(
    query: CallbackQuery, callback_data: SaveMessageData, bot: Bot, **kwargs
):
    logger.info("Received data on chosen action: {}".format(callback_data))
    message_id = callback_data.message_id
    await update_action_for_message(message_id, callback_data.action)
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


def actions_menu_by_content_type_kb(
    message_id: str, content_type: ContentType
) -> types.InlineKeyboardMarkup:
    message_actions = actions_by_content_type.get(
        content_type, actions_by_content_type[ContentType.TEXT]
    )
    return _build_message_actions_menu_kb(message_actions, message_id, content_type)


def _build_message_actions_menu_kb(
    actions: list, message_id: str, content_type: str
) -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for action in actions:
        kb_builder.button(
            text=caption_by_action[action],
            callback_data=SaveMessageData(
                action=action, message_id=message_id, content_type=content_type
            ),
        )
    return kb_builder.as_markup()
