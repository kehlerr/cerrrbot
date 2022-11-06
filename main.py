#!/usr/bin/env python3

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Callable, List
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command, CommandObject, callback_data
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


from settings import TOKEN
from pass_helper import PASS_APP


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


main_router = Router()
pass_form_router = Router()

class PassForm(StatesGroup):
    pass_to_enter = State()
    pass_add_new = State()
    pass_edit_menu = State()
    pass_append = State()
    pass_overwrite = State()

class Action(str, Enum):
    cancel = "CANCEL"
    nav_prev = "NAV_PREV"
    nav_next = "NAV_NEXT"
    edit_overwrite = "EDIT_OVERWRITE"
    edit_append = "EDIT_APPEND"


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


@pass_form_router.message(Command(commands=["pass_show"]))
async def cmd_pass_show(message: types.Message, state: FSMContext, command: CommandObject):
    pass_path = command.args

    if not pass_path:
        answer_txt = "Empty pass path"
    else:
        passphrase = PASS_APP.show(pass_path)
        if passphrase:
            answer_txt = f"<tg-spoiler>{passphrase}</tg-spoiler>"
        else:
            answer_txt = "Some error occured"

    answer = await message.reply(answer_txt, disable_notification=True, parse_mode="HTML")
    await delete_messages_after_timeout([message, answer])


@pass_form_router.message(Command(commands=["pass_add"]))
async def cmd_pass_add(message: types.Message, state: FSMContext, command: CommandObject):

    pass_enter_data = PassEnterData("Enter password:", PassForm.pass_add_new, back_to_main_menu_kb)
    await state.update_data(pass_enter_data=pass_enter_data)

    pass_path = command.args
    if pass_path:
        await _on_got_new_pass_path(message, state, pass_path)
    else:
        await state.set_state(PassForm.pass_to_enter)
        pass_enter_data.prompt_msg = await message.answer(
            "Enter new pass location:", reply_markup=back_to_main_menu_kb()
        )
        await message.delete()


@pass_form_router.message(Command(commands=["pass_edit"]))
async def cmd_pass_edit(message: types.Message, state: FSMContext, command: CommandObject):
    pass_enter_data = PassEnterData("Choose variant of edit:", PassForm.pass_edit_menu, pass_edit_menu_kb)
    await state.update_data(pass_enter_data=pass_enter_data)

    pass_path = command.args
    if pass_path:
        await _on_got_new_pass_path(message, state, pass_path)
    else:
        await state.set_state(PassForm.pass_to_enter)
        pass_enter_data.prompt_msg = await message.answer(
            "Enter pass location to edit:", reply_markup=back_to_main_menu_kb()
        )
        await message.delete()


@pass_form_router.message(PassForm.pass_to_enter)
async def add_pass_enter_pass_path(message: types.Message, state: FSMContext):
    await _on_got_new_pass_path(message, state, message.text)


async def _on_got_new_pass_path(message: types.Message, state: FSMContext, pass_path: str):
    state_data = await state.get_data()
    pass_enter_data = state_data.get("pass_enter_data")
    pass_enter_data.pass_path = pass_path
    await state.set_state(pass_enter_data.next_state)

    prompt_msg = pass_enter_data.prompt_msg
    if prompt_msg:
        await prompt_msg.edit_text(
            pass_enter_data.next_prompt, reply_markup=pass_enter_data.reply_markup()
        )
    else:
        pass_enter_data.prompt_msg = await message.answer(
            pass_enter_data.next_prompt, reply_markup=pass_enter_data.reply_markup()
        )

    await message.delete()


@pass_form_router.message(PassForm.pass_add_new)
async def on_cmd_pass_add(message: types.Message, state: FSMContext):
    await _on_entered_password(message, state, "New password successfully added", None)

@pass_form_router.message(PassForm.pass_edit_menu)
async def pass_edit_menu(message: types.Message):
    await message.answer("Choose variant of edit:", reply_markup=pass_edit_menu_kb())
    await message.delete()


@pass_form_router.callback_query(UserAction.filter(F.action == Action.edit_append))
async def enter_password_to_append(query, state: FSMContext):
    await state.set_state(PassForm.pass_append)
    await query.message.edit_text("[Append] Enter new password:", reply_markup=back_to_main_menu_kb())


@pass_form_router.message(PassForm.pass_append)
async def cmd_pass_append(message: types.Message, state: FSMContext):
    await _on_entered_password(message, state, "Password successfully appended", None)


@pass_form_router.callback_query(UserAction.filter(F.action == Action.edit_overwrite))
async def enter_password_to_append(query, state: FSMContext):
    await state.set_state(PassForm.pass_overwrite)
    await query.message.edit_text("[Overwrite] Enter new password:", reply_markup=back_to_main_menu_kb())


@pass_form_router.message(PassForm.pass_overwrite)
async def cmd_pass_overwrite(message: types.Message, state: FSMContext):
    await _on_entered_password(message, state, "Password successfully overwritten", None)


async def _on_entered_password(
    message: types.Message,
    state: FSMContext,
    reply_txt: str,
    pass_action: Callable
):
    password = message.text
    state_data = await state.get_data()
    await state.clear()
    pass_enter_data = state_data.get("pass_enter_data")
    pass_path = pass_enter_data.pass_path
    await message.delete()
    prompt_msg = pass_enter_data.prompt_msg
    try:
        await prompt_msg.delete()
    except AttributeError as exc:
        logger.exception("Empty prompt message:", str(exc))

    reply = await message.answer(reply_txt)
    await delete_messages_after_timeout([reply])


@main_router.message(Command(commands=["pass", "pass_menu"]))
@main_router.callback_query(MenuAppData.filter(F.app_name == MenuApp.pass_app))
@pass_form_router.callback_query(UserAction.filter(F.action == Action.cancel))
async def show_pass_menu(message: types.Message, bot: Bot, state: FSMContext, callback_data: UserAction, event_chat):
    logger.info(f"[{message.from_user}] Shown pass_menu")
    print(callback_data)
    prompt = "Choose action for pass store:"
    commands = (
        "/pass_add - add new password",
        "/pass_list - show stored passwords",
        "/pass_edit - change some password"
    )
    pass_menu_txt = "\n".join((prompt, *commands))
    await state.clear()
    await message.answer("Returning")
    await bot.send_message(text=pass_menu_txt, chat_id=event_chat.id, reply_markup=back_to_main_menu_kb())


@main_router.message(Command(commands=["rtorrent"]))
@main_router.callback_query(MenuAppData.filter(F.app_name == MenuApp.rtorrent))
async def show_rtorrent_menu(message: types.Message, bot: Bot, event_chat):
    await message.answer(text="will be soon")


@pass_form_router.callback_query(UserAction.filter(F.action.in_({Action.nav_prev, Action.nav_next})))
async def navigate_content(query, callback_data: UserAction, state: FSMContext):
    direction = 1 if callback_data.action == Action.nav_next else -1
    await show_nav_content(query.message, state, direction)


async def show_nav_content(message: types.Message, state: FSMContext, direction: int = 0):
    state_data = await state.get_data()
    content = state_data.get("content_data")
    if not content or not content.data:
        return

    content_size = len(content.data)

    content_limit = content.page_limit
    nav_idx = state_data.get("nav_idx", 0)
    nav_idx += direction * content_limit
    if nav_idx < 0 or nav_idx > content_size:
        return

    reply_markup = None
    if content_size < content_limit:
        reply_markup = back_to_main_menu_kb()
    else:
        if nav_idx - content_limit < 0:
            reply_markup = nav_menu_without_prev_kb()

        if nav_idx + content_limit >= content_size:
            reply_markup = nav_menu_without_next_kb()

        await state.update_data(nav_idx=nav_idx)

    data_part = content.data[nav_idx:nav_idx+content_limit]
    answer_text = "\n".join(data_part)

    reply_markup = reply_markup or nav_menu_kb()
    if direction == 0 and nav_idx == 0:
        await message.answer(answer_text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await message.edit_text(answer_text, reply_markup=reply_markup, parse_mode="HTML")


@main_router.message(Command(commands=["pass_list"]))
async def pass_list_cmd(message: types.Message, state: FSMContext, command: CommandObject):
    passes_data = PASS_APP.get_passes_list(command.args)

    content = [f"<code>{pass_}/</code>" for pass_ in passes_data["passsubdirs"]]
    content.extend([f"<code>{pass_}</code>" for pass_ in passes_data["passfiles"]])
    content = ContentData(content, 25)

    await state.update_data({"content_data": content})
    await show_nav_content(message, state)

@main_router.message(Command(commands=["start", "menu"]))
async def main_menu(message: types.Message):
    await show_main_menu(message)


@pass_form_router.callback_query(UserAction.filter(F.action == Action.cancel))
async def on_cancel_btn_pressed(query, callback_data, bot: Bot, state: FSMContext, event_chat):
    await bot.send_message(chat_id=event_chat.id, text="Welcome, master!", reply_markup=main_menu_kb())

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

def back_to_main_menu_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))

    return kb_builder.as_markup()


def pass_edit_menu_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Append", callback_data=UserAction(action=Action.edit_append))
    kb_builder.button(text="Owerwrite", callback_data=UserAction(action=Action.edit_overwrite))
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))

    return kb_builder.as_markup()


def nav_menu_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="<-", callback_data=UserAction(action=Action.nav_prev))
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))
    kb_builder.button(text="->", callback_data=UserAction(action=Action.nav_next))

    return kb_builder.as_markup()


def nav_menu_without_next_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="<-", callback_data=UserAction(action=Action.nav_prev))
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))

    return kb_builder.as_markup()


def nav_menu_without_prev_kb() -> types.InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Cancel", callback_data=UserAction(action=Action.cancel))
    kb_builder.button(text="->", callback_data=UserAction(action=Action.nav_next))

    return kb_builder.as_markup()


@dataclass
class ContentData:
    data: dict
    page_limit: int = 10


@dataclass
class PassEnterData:
    next_prompt: str
    next_state: Action
    reply_markup: Callable
    pass_path: str = ""
    prompt_msg: types.Message = None


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