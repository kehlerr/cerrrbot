import html
import logging
from dataclasses import dataclass
from functools import partial
from typing import Callable

from aiogram import Bot, F, Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from common import (
    Action,
    ContentData,
    UserAction,
    delete_messages_after_timeout,
    show_nav_content,
)
from keyboards import Keyboards as kbs
from keyboards import UserActionKeyboard
from pass_helper import PASS_APP

logger = logging.getLogger(__name__)

pass_form_router = Router()


class PassEditMenuKb(UserActionKeyboard):
    buttons_data = (
        ("Append", Action.edit_append),
        ("Overwrite", Action.edit_overwrite),
        ("Cancel", Action.cancel),
    )


kbs.pass_edit_menu = PassEditMenuKb()


class PassForm(StatesGroup):
    pass_to_enter = State()
    pass_add_new = State()
    pass_edit_menu = State()
    pass_append = State()
    pass_overwrite = State()
    pass_to_enter_otp = State()


@dataclass
class PassEnterData:
    next_prompt: str
    next_state: Action
    reply_markup: Callable
    pass_path: str = ""
    prompt_msg: types.Message = None


@pass_form_router.message(Command(commands=["pass_show"]))
async def cmd_pass_show(
    message: types.Message,
    state: FSMContext,
    command: CommandObject,
    bot: Bot,
    event_chat,
):
    await message.delete()
    pass_path = command.args
    if not pass_path:
        await state.clear()
        answer = await bot.send_message(
            text="Empty pass path", disable_notification=True, chat_id=event_chat.id
        )
        await delete_messages_after_timeout([answer])
        return

    callback = partial(impl_pass_show, message, pass_path)
    await action_on_auth(message, state, bot, event_chat, callback)


async def action_on_auth(
    message: types.Message, state: FSMContext, bot: Bot, event_chat, callback: Callable
):
    if PASS_APP.is_authorized:
        await callback(state)
        return

    answer = await bot.send_message(
        text="Enter OTP:",
        disable_notification=True,
        chat_id=event_chat.id,
        reply_markup=kbs.back_to_main_menu,
    )
    await state.set_state(PassForm.pass_to_enter_otp)
    await state.update_data(callback=callback, prompt_msg=answer)


async def impl_pass_show(message: types.Message, pass_path: str, state: FSMContext):
    passphrase = PASS_APP.show(pass_path)
    if passphrase:
        passphrase = html.escape(passphrase)
        answer = await message.answer(
            f"<tg-spoiler>{passphrase}</tg-spoiler>", parse_mode="HTML"
        )
    else:
        answer = await message.answer("Some error occured")

    await state.clear()
    await delete_messages_after_timeout([answer], timeout=7)


@pass_form_router.message(Command(commands=["pass_add"]))
async def cmd_pass_add(message: types.Message, state: FSMContext, command: CommandObject):

    pass_enter_data = PassEnterData(
        "Enter password:", PassForm.pass_add_new, kbs.back_to_main_menu
    )
    await state.update_data(pass_enter_data=pass_enter_data)

    pass_path = command.args
    if pass_path:
        await _on_got_new_pass_path(message, state, pass_path)
    else:
        await state.set_state(PassForm.pass_to_enter)
        pass_enter_data.prompt_msg = await message.answer(
            "Enter new pass location:", reply_markup=kbs.back_to_main_menu
        )
        await message.delete()


@pass_form_router.message(Command(commands=["pass_edit"]))
async def cmd_pass_edit(
    message: types.Message, state: FSMContext, command: CommandObject
):
    pass_enter_data = PassEnterData(
        "Choose variant of edit:", PassForm.pass_edit_menu, kbs.pass_edit_menu
    )
    await state.update_data(pass_enter_data=pass_enter_data)

    pass_path = command.args
    if pass_path:
        await _on_got_new_pass_path(message, state, pass_path)
    else:
        await state.set_state(PassForm.pass_to_enter)
        pass_enter_data.prompt_msg = await message.answer(
            "Enter pass location to edit:", reply_markup=kbs.back_to_main_menu
        )
        await message.delete()


@pass_form_router.message(PassForm.pass_to_enter)
async def add_pass_enter_pass_path(message: types.Message, state: FSMContext):
    await _on_got_new_pass_path(message, state, message.text)


@pass_form_router.message(PassForm.pass_to_enter_otp)
async def on_got_otp(message: types.Message, state: FSMContext):
    await message.delete()

    if PASS_APP.authorize(message.text):
        state_data = await state.get_data()
        callback = state_data.get("callback")
        if callback:
            await callback(state)

        prompt_msg = state_data.get("prompt_msg")
        if prompt_msg:
            await prompt_msg.delete()


async def _on_got_new_pass_path(
    message: types.Message, state: FSMContext, pass_path: str
):
    state_data = await state.get_data()
    pass_enter_data = state_data.get("pass_enter_data")
    pass_enter_data.pass_path = pass_path
    await state.set_state(pass_enter_data.next_state)

    prompt_msg = pass_enter_data.prompt_msg
    if prompt_msg:
        await prompt_msg.edit_text(
            pass_enter_data.next_prompt, reply_markup=pass_enter_data.reply_markup
        )
    else:
        pass_enter_data.prompt_msg = await message.answer(
            pass_enter_data.next_prompt, reply_markup=pass_enter_data.reply_markup
        )

    await message.delete()


@pass_form_router.message(PassForm.pass_add_new)
async def on_cmd_pass_add(message: types.Message, state: FSMContext):
    await _on_entered_password(
        message, "New password successfully added", PASS_APP.add_new_pass, state
    )


@pass_form_router.message(PassForm.pass_edit_menu)
async def pass_edit_menu(message: types.Message):
    await message.answer("Choose variant of edit:", reply_markup=kbs.pass_edit_menu)
    await message.delete()


@pass_form_router.callback_query(UserAction.filter(F.action == Action.edit_append))
async def enter_password_to_append(query, state: FSMContext):
    await state.set_state(PassForm.pass_append)
    await query.message.edit_text(
        "[Append] Enter new password:", reply_markup=kbs.back_to_main_menu
    )


@pass_form_router.message(PassForm.pass_append)
async def cmd_edit_append(
    message: types.Message, state: FSMContext, bot: Bot, event_chat
):
    callback = partial(
        _on_entered_password,
        message,
        "Password successfully appended",
        PASS_APP.edit_append,
    )
    await action_on_auth(message, state, bot, event_chat, callback)


@pass_form_router.callback_query(UserAction.filter(F.action == Action.edit_overwrite))
async def enter_password_to_overwrite(query, state: FSMContext):
    await state.set_state(PassForm.pass_overwrite)
    await query.message.edit_text(
        "[Overwrite] Enter new password:", reply_markup=kbs.back_to_main_menu
    )


@pass_form_router.message(PassForm.pass_overwrite)
async def cmd_edit_overwrite(
    message: types.Message, state: FSMContext, bot: Bot, event_chat
):
    callback = partial(
        _on_entered_password,
        message,
        "Password successfully overwritten",
        PASS_APP.edit_overwrite,
    )
    await action_on_auth(message, state, bot, event_chat, callback)


async def _on_entered_password(
    message: types.Message, reply_txt: str, pass_action: Callable, state: FSMContext
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

    try:
        pass_action(pass_path, password)
    except Exception as exc:
        logger.exception("Error occurred while executing pass callback: %s", str(exc))

    reply = await message.answer(reply_txt)
    await delete_messages_after_timeout([reply])


@pass_form_router.message(Command(commands=["pass_list"]))
async def pass_list_cmd(
    message: types.Message, state: FSMContext, command: CommandObject
):
    passes_data = PASS_APP.list_passes(command.args)

    content = []
    try:
        content.extend([f"<code>{pass_}/</code>" for pass_ in passes_data["passsubdirs"]])
    except KeyError:
        pass

    try:
        content.extend([f"<code>{pass_}</code>" for pass_ in passes_data["passfiles"]])
    except KeyError:
        pass

    content = ContentData(content)

    await state.update_data({"content_data": content})
    await show_nav_content(message, state)
