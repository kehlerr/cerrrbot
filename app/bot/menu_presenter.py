from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger

from app import app_settings
from app.actions import MessageActions
from app.exceptions import InvalidMessageDocumentError
from app.models import ActionResult, MessageAction, MessageDocument, SVM_ReplyInfo

from .types import ActionCallbackData


class MenuPresenter:
    @classmethod
    def get_reply_info(cls, msgdoc: MessageDocument, action_result: ActionResult | None = None) -> SVM_ReplyInfo:
        if not (msgdoc_info := msgdoc.cb_message_info):
            raise InvalidMessageDocumentError(f"Message document {msgdoc.id} has no cb_message_info", msgdoc=msgdoc)

        if not action_result:
            action_result = ActionResult()

        reply_actions = []
        for action_code, action_data in msgdoc_info.get_current_menu().items():
            action = MessageActions.BY_CODE[action_code]
            if additional_caption := action_data.get("additional_caption", ""):
                action = action.model_copy(update={"caption": f"{action.caption}{additional_caption}"}, deep=True)
            reply_actions.append(action)

        return SVM_ReplyInfo(
            actions=sorted(reply_actions),
            reply_action_message_id=msgdoc_info.reply_action_message_id,
            result_info_text=action_result.popup_text,
            need_update_buttons=action_result.actions_updated,
        )

    @classmethod
    def build_message_actions_menu_kb(cls, reply_actions: list[MessageAction], msgdoc: MessageDocument) -> InlineKeyboardMarkup:

        if not (msgdoc_id := msgdoc.id):
            raise InvalidMessageDocumentError("Message document has no id", msgdoc=msgdoc)

        actions_buttons = []
        custom_actions_buttons: dict[int, list[InlineKeyboardButton]] = {}
        logger.debug(f"Adding actions for: {msgdoc_id}")
        for action in reply_actions:
            logger.debug(f"Adding action: {action}")
            button = InlineKeyboardButton(
                text=action.caption,
                callback_data=ActionCallbackData(action=action.code, msgdoc_id=msgdoc.id).pack(),
            )
            if action.order >= app_settings.custom_message_min_order:
                custom_actions_buttons.setdefault(action.order // 100, []).append(button)
            else:
                actions_buttons.append(button)

        kb_builder = InlineKeyboardBuilder()
        kb_builder.row(*actions_buttons)
        for buttons in custom_actions_buttons.values():
            kb_builder.row(*buttons)

        return kb_builder.as_markup()
