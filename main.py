#!/usr/bin/env python3

from ast import Pass
from enum import Enum
from typing import List, Optional
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from aiogram.handlers import CallbackQueryHandler


import asyncio
from aiogram import Bot, Dispatcher, types, Router, F
#from aiogram.contrib.memory import MemoryStorage
from aiogram.filters import Command, CommandObject, callback_data
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram.utils.helper import Helper, HelperMode, Item

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


from settings import TOKEN
from pass_helper import PASS_APP

pass_form_router = Router()

class PassForm(StatesGroup):
    pass_show = State()
    pass_path = State()
    pass_enter = State()
    pass_to_enter = State()


main_router = Router()

logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)
log_handler = TimedRotatingFileHandler('main.log', when='s', interval=10, backupCount=5)
log_handler_stream = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s][%(asctime)s] %(message)s', '%m/%d/%Y-%H:%M:%S')
log_handler.setFormatter(formatter)
log_handler_stream.setFormatter(formatter)
#logger.addHandler(log_handler)
logger.addHandler(log_handler_stream)


TEXT_CANCEL = u"Cancel\U0000274C"


class Action(str, Enum):
    cancel = "CANCEL"


class UserAction(callback_data.CallbackData, prefix="user"):
    action: Action


class MenuApp(str, Enum):
    pass_app = "Pass app"
    rtorrent = "RTORRENT"


class MenuAppData(callback_data.CallbackData, prefix="menu"):
    app_name: MenuApp


async def process_entered_passphrase(message: types.Message, state: FSMContext):
    argument = message["text"]

    if argument == "12345":
        answer = PASS_APP.show()
    else:
        answer = "Incorrect passphrase"

    replied = await message.reply(answer, parse_mode="HTML", disable_notification=True)
    await delete_messages_after_timeout([message, replied])


#@dp.message_handler(commands="pass_list")
async def cmd_pass_list(message: types.Message):
    subdir = message.get_args()
    answer = PASS_APP.list_passes(subdir)
    replied_message = await message.reply(answer, parse_mode="HTML")
    await delete_messages_after_timeout([replied_message, message])


#@dp.message_handler(commands="pass_show")
async def cmd_pass_show(message: types.Message, state: FSMContext):
    pass_path = message.get_args()

    if not pass_path:
        reply = await message.reply("Empty pass path", disable_notification=True)
    else:
        await state.set_state(PassForm.pass_show)
        await state.update_data(requested_pass=pass_path)
        replied_message = await message.reply("Enter passphrase:", disable_notification=True)
    await delete_messages_after_timeout([message, replied_message])


@pass_form_router.message(Command(commands=["pass_add"]))
async def cmd_pass_add(message: types.Message, state: FSMContext, command: CommandObject):
    pass_path = command.args

    if pass_path:
        await state.update_data(pass_path=pass_path)
        await _on_got_new_pass_path(message, state)
    else:
        await state.set_state(PassForm.pass_to_enter)
        await message.answer("Enter new pass location:", reply_markup=back_to_main_menu_kb(message))


@pass_form_router.message(PassForm.pass_to_enter)
async def on_enter_password(message: types.Message, state: FSMContext):
    pass_path = message.text
    await state.update_data(pass_path=pass_path)
    await _on_got_new_pass_path(message, state)


async def _on_got_new_pass_path(message: types.Message, state: FSMContext):
    await state.set_state(PassForm.pass_enter)
    await message.answer("Enter password:", reply_markup=back_to_main_menu_kb(message))


@pass_form_router.message(PassForm.pass_enter)
async def on_entered_password(message: types.Message, state: FSMContext):
    password = message.text
    state_data = await state.get_data()
    pass_path = state_data.get("pass_path")
    await message.answer(f"Entered pass path {pass_path} and password: {password}")


@main_router.message(Command(commands=["start", "menu"]))
async def main_menu(message: types.Message):
    await show_main_menu(message)


#@dp.message_handler(state="*", content_types=types.message.ContentType.TEXT)
async def message_txt(message: types.Message):
    await delete_messages_after_timeout([message], timeout=60)


@pass_form_router.callback_query(UserAction.filter(F.action == Action.cancel))
async def on_cancel_btn_pressed(query, callback_data, bot: Bot, state: FSMContext, event_chat):
    await bot.send_message(chat_id=event_chat.id, text="Welcome, master!", reply_markup=main_menu_kb())
    #await message.answer("Welcome, master", reply_markup=main_menu_kb())


@main_router.message(Command(commands=["pass", "pass_menu"]))
@main_router.callback_query(MenuAppData.filter(F.app_name == MenuApp.pass_app))
@pass_form_router.callback_query(UserAction.filter(F.action == Action.cancel))
async def show_pass_menu(message: types.Message, bot: Bot, event_chat):
    logger.info(f"[{message.from_user}] Showed pass_menu")
    prompt = "Choose action for pass store:"
    commands = (
        "/pass_add - add new password",
        "/pass_list - show stored passwords",
        "/pass_edit - change some password"
    )
    pass_menu_txt = "\n".join((prompt, *commands))

    await bot.send_message(text=pass_menu_txt, chat_id=event_chat.id, reply_markup=back_to_main_menu_kb(message))

@main_router.message(Command(commands=["rtorrent"]))
@main_router.callback_query(MenuAppData.filter(F.app_name == MenuApp.rtorrent))
async def show_rtorrent_menu(message: types.Message, bot: Bot, event_chat):
    await message.answer(text="will be soon")
    #await bot.send_message(text="Will be soon...", chat_id=event_chat.id)

###############
# Common funcs
###############

async def show_main_menu(message: types.Message):
    keyboard = main_menu_kb()
    await message.answer("Welcome, master", reply_markup=keyboard)

def main_menu_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for app in MenuApp:
        kb_builder.button(text=app.value.title(), callback_data=MenuAppData(app_name=app))
    return kb_builder.as_markup()

def back_to_main_menu_kb(message) -> types.InlineKeyboardMarkup:
    logger.info(f"[{message.from_user}] Pressed back_to_main_menu")
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))

    return kb_builder.as_markup()

async def delete_messages_after_timeout(messages: List[types.Message], timeout=15):
    await asyncio.sleep(timeout)
    for message in messages:
        await message.delete()


async def main():
    logger.info("Start bot...")
    bot = Bot(token=TOKEN)

    dp = Dispatcher()
    dp.include_router(main_router)
    dp.include_router(pass_form_router)
    await dp.start_polling(bot)
    logger.info("Bot started")


if __name__ == "__main__":
    #logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())