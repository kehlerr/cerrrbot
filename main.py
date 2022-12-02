#!/usr/bin/env python3

import asyncio
import logging
from enum import Enum
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.filters import Command, callback_data
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

import db_utils
import savmes
from commands_pass import pass_form_router
from commands_savmes import savmes_router
from common import navigate_content
from constants import Action, UserAction
from keyboards import Keyboards as kbs
from settings import TOKEN

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_handler = TimedRotatingFileHandler("main.log", when="s", interval=10, backupCount=5)
log_handler_stream = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(levelname)s][%(asctime)s] %(message)s", "%m/%d/%Y-%H:%M:%S"
)
log_handler.setFormatter(formatter)
log_handler_stream.setFormatter(formatter)
# logger.addHandler(log_handler)
logger.addHandler(log_handler_stream)


main_router = Router()
main_router.callback_query.register(
    navigate_content,
    UserAction.filter(F.action.in_({Action.nav_prev, Action.nav_next})),
)

others_router = Router()


class MenuApp(str, Enum):
    pass_app = "Pass app"
    rtorrent = "RTORRENT"


class MenuAppData(callback_data.CallbackData, prefix="menu"):
    app_name: MenuApp


@main_router.message(Command(commands=["pass", "pass_menu"]))
@main_router.callback_query(MenuAppData.filter(F.app_name == MenuApp.pass_app))
async def show_pass_menu(
    message: types.Message, bot: Bot, state: FSMContext, event_chat
):
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
        kb_builder.button(
            text=app.value.title(), callback_data=MenuAppData(app_name=app)
        )
    return kb_builder.as_markup()


async def scheduled(wait_for=150):
    while True:
        logger.debug("Waiting for new tasks...")
        savmes.check_actions_on_new_messages()
        await asyncio.sleep(wait_for)


async def main():

    logger.info("Checking db...")
    db_info = db_utils.check_connection()
    if db_info:
        logger.debug("Got db:{}".format(db_info))
    else:
        logger.error("DB is down")

    logger.info("Start bot...")
    bot = Bot(token=TOKEN)

    loop = asyncio.get_event_loop()
    loop.create_task(scheduled())

    dp = Dispatcher()
    dp.include_router(main_router)
    dp.include_router(pass_form_router)
    dp.include_router(savmes_router)
    dp.include_router(others_router)
    await dp.start_polling(bot)
    logger.info("Bot started")


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
