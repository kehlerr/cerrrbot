from loguru import logger
from typing import cast

from dishka.integrations.aiogram import FromDishka, inject

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from app.actions import MessageActions
from app.exceptions import AppError
from app.models import ActionResult, MessageDocument
from app.notifications import NotificationService
from app.savmes import SavmesService
from app.types import ActionCallbackData

from .menu_presenter import MenuPresenter


handlers_router = Router()


@handlers_router.message()
@inject
async def on_received_message(message: Message, bot: Bot, savmes_service: FromDishka[SavmesService]) -> None:
    logger.debug(f"Received new message: {message}")

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        msgdoc = await savmes_service.add_new_message(message)
    except AppError as app_error_exc:
        logger.error("Error occured while adding received message: %s", app_error_exc.detail)
        await message.answer("Error occured while adding message.\nPlease try again later or check logs.")
        return

    reply_info = MenuPresenter.get_reply_info(msgdoc)
    if not reply_info.actions:
        return

    reply_action_message = await message.reply(
        "Choose action for message:",
        reply_markup=MenuPresenter.build_message_actions_menu_kb(reply_info.actions, msgdoc),
    )
    await savmes_service.set_reply_action_message_id(msgdoc, reply_action_message.message_id)


@handlers_router.callback_query(ActionCallbackData.filter(F.action.in_(MessageActions.BY_CODE)))
@inject
async def on_action_pressed(
    query: CallbackQuery, callback_data: ActionCallbackData, bot: Bot, savmes_service: FromDishka[SavmesService]
) -> None:
    logger.info("Received data on chosen action: {}".format(callback_data))

    msgdoc_id = callback_data.msgdoc_id
    if not (msgdoc := await savmes_service.get_msgdoc_by_id(msgdoc_id)):
        logger.warning("Message for action not found: {}".format(msgdoc_id))
        return

    result = await savmes_service.execute_message_action(msgdoc, bot, callback_data.action)
    await _process_action_result(bot, msgdoc, result, query=query)


@inject
async def perform_message_actions(bot: Bot, savmes_service: FromDishka[SavmesService]) -> None:
    for msgdoc in await savmes_service.get_messages_to_execute_actions():
        result = await savmes_service.execute_message_action(msgdoc, bot)
        await _process_action_result(bot, msgdoc, result)


async def _process_action_result(
    bot: Bot,
    msgdoc: MessageDocument,
    action_result: ActionResult,
    query: CallbackQuery | None = None,
) -> None:

    if action_result.message_gone:
        return

    reply_info = MenuPresenter.get_reply_info(msgdoc, action_result=action_result)

    if reply_info.actions:
        next_markup = MenuPresenter.build_message_actions_menu_kb(reply_info.actions, msgdoc)
    else:
        next_markup = None

    if query:
        if reply_info.result_info_text:
            await query.answer(reply_info.result_info_text)
        if next_markup and reply_info.need_update_buttons:
            await cast(Message, query.message).edit_reply_markup(reply_markup=next_markup)
        return

    if not reply_info.reply_action_message_id or not reply_info.need_update_buttons:
        return

    await bot.edit_message_reply_markup(
        chat_id=msgdoc.chat.id,
        message_id=reply_info.reply_action_message_id,
        reply_markup=next_markup
    )


@inject
async def delete_deprecated_messages(bot: Bot, savmes_service: FromDishka[SavmesService]) -> None:
    await savmes_service.delete_deprecated_messages(bot)


@inject
async def process_notifications(bot: Bot, notification_service: FromDishka[NotificationService]) -> None:
    await notification_service.process_notifications(bot)
