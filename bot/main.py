#!/usr/bin/env python3

import asyncio
import logging
from enum import Enum

import db_utils
import savmes
import notifications
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command, callback_data
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from commands_pass import pass_form_router
from common import CheckUserMiddleware, navigate_content
from constants import CHECK_FOR_NEW_MESSAGES_TIMEOUT, CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT, CHECK_FOR_NOTIFICATIONS, Action, UserAction
from keyboards import Keyboards as kbs
from settings import TOKEN

logger = logging.getLogger("cerrrbot")
logger.setLevel(logging.DEBUG)
log_handler_stream = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(levelname)s][%(asctime)s] %(message)s", "%m/%d/%Y-%H:%M:%S"
)
log_handler_stream.setFormatter(formatter)
logger.addHandler(log_handler_stream)


scheduler = AsyncIOScheduler()


main_router = Router()
main_router.callback_query.register(
    navigate_content,
    UserAction.filter(F.action.in_({Action.nav_prev, Action.nav_next})),
)
main_router.message.middleware(CheckUserMiddleware())


class MenuApp(str, Enum):
    pass_app = "Pass app"
    rtorrent = "RTORRENT"


class MenuAppData(callback_data.CallbackData, prefix="menu"):
    app_name: str


@main_router.message(Command(commands=["pass", "pass_menu"]))
@main_router.callback_query(MenuAppData.filter(F.app_name == MenuApp.pass_app))
async def show_pass_menu(message: types.Message, bot: Bot, state: FSMContext, event_chat):
    logger.info(f"[{message.from_user}] Shown pass_menu")
    prompt = "Choose action for pass store:"
    commands = (
        "/pass_add - add new password",
        "/pass_list - show stored passwords",
        "/pass_edit - change some password",
    )
    pass_menu_txt = "\n".join((prompt, *commands))
    await state.clear()
    await message.answer("Returning")
    await bot.send_message(
        text=pass_menu_txt, chat_id=event_chat.id, reply_markup=kbs.back_to_main_menu
    )


@main_router.message(Command(commands=["rtorrent"]))
@main_router.callback_query(MenuAppData.filter(F.app_name == MenuApp.rtorrent))
async def show_rtorrent_menu(message: types.Message, bot: Bot, event_chat):
    await message.answer(text="will be soon")


@main_router.message(Command(commands=["start", "menu"]))
async def main_menu(message: types.Message):
    await show_main_menu(message)


async def show_main_menu(message: types.Message):
    keyboard = main_menu_kb()
    await message.answer("Welcome, master", reply_markup=keyboard)


def main_menu_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for app in MenuApp:
        kb_builder.button(text=app.value.title(), callback_data=MenuAppData(app_name=app))
    return kb_builder.as_markup()


async def create_periodic_tasks(event_loop, bot: Bot) -> None:
    scheduler.add_job(savmes.perform_message_actions, "interval", (bot,), seconds=CHECK_FOR_NEW_MESSAGES_TIMEOUT)
    scheduler.add_job(savmes.delete_deprecated_messages, "interval", (bot,), seconds=CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT)
    scheduler.add_job(notifications.process_notifications, "interval", (bot,), seconds=CHECK_FOR_NOTIFICATIONS)
    scheduler.start()


async def main():
    logger.debug("Checking db...")
    db_info = db_utils.check_connection()
    if db_info:
        logger.debug("Got db:{}".format(db_info))
        db_utils.init_db()
    else:
        logger.error("DB is down")

    logger.info("Start bot...")
    bot = Bot(token=TOKEN)

    loop = asyncio.get_event_loop()
    await create_periodic_tasks(loop, bot)

    main_router.include_router(pass_form_router)
    main_router.include_router(savmes.router)

    dp = Dispatcher()
    dp.include_router(main_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception(str(exc))
        exit(-1)
