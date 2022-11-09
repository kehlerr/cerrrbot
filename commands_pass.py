import logging

from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, CommandObject
from aiogram.fsm.state import State, StatesGroup
from dataclasses import dataclass
from typing import Callable

from common import Action, UserAction, delete_messages_after_timeout, show_nav_content, ContentData
from keyboards import Keyboards as kbs, UserActionKeyboard
from pass_helper import PASS_APP


logger = logging.getLogger(__name__)


class PassEditMenuKb(UserActionKeyboard):
    buttons_data = (
        ("Append", Action.edit_append),
        ("Overwrite", Action.edit_overwrite),
        ("Cancel", Action.cancel),
    )

kbs.pass_edit_menu = PassEditMenuKb()

pass_form_router = Router()


class PassForm(StatesGroup):
    pass_to_enter = State()
    pass_add_new = State()
    pass_edit_menu = State()
    pass_append = State()
    pass_overwrite = State()

@dataclass
class PassEnterData:
    next_prompt: str
    next_state: Action
    reply_markup: Callable
    pass_path: str = ""
    prompt_msg: types.Message = None


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

    pass_enter_data = PassEnterData("Enter password:", PassForm.pass_add_new, kbs.back_to_main_menu)
    await state.update_data(pass_enter_data=pass_enter_data)

    pass_path = command.args
    if pass_path:
        await _on_got_new_pass_path(message, state, pass_path)
    else:
        await state.set_state(PassForm.pass_to_enter)
        pass_enter_data.prompt_msg = await message.answer(
            "Enter new pass location:", reply_markup=kbs.back_to_main_menu_kb
        )
        await message.delete()


@pass_form_router.message(Command(commands=["pass_edit"]))
async def cmd_pass_edit(message: types.Message, state: FSMContext, command: CommandObject):
    pass_enter_data = PassEnterData("Choose variant of edit:", PassForm.pass_edit_menu, kbs.pass_edit_menu)
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
    await message.answer("Choose variant of edit:", reply_markup=kbs.pass_edit_menu)
    await message.delete()


@pass_form_router.callback_query(UserAction.filter(F.action == Action.edit_append))
async def enter_password_to_append(query, state: FSMContext):
    await state.set_state(PassForm.pass_append)
    await query.message.edit_text("[Append] Enter new password:", reply_markup=kbs.back_to_main_menu)


@pass_form_router.message(PassForm.pass_append)
async def cmd_pass_append(message: types.Message, state: FSMContext):
    await _on_entered_password(message, state, "Password successfully appended", None)


@pass_form_router.callback_query(UserAction.filter(F.action == Action.edit_overwrite))
async def enter_password_to_append(query, state: FSMContext):
    await state.set_state(PassForm.pass_overwrite)
    await query.message.edit_text("[Overwrite] Enter new password:", reply_markup=kbs.back_to_main_menu)


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


@pass_form_router.message(Command(commands=["pass_list"]))
async def pass_list_cmd(message: types.Message, state: FSMContext, command: CommandObject):
    passes_data = PASS_APP.list_passes(command.args)

    content = [f"<code>{pass_}/</code>" for pass_ in passes_data["passsubdirs"]]
    content.extend([f"<code>{pass_}</code>" for pass_ in passes_data["passfiles"]])
    content = ContentData(content)

    await state.update_data({"content_data": content})
    await show_nav_content(message, state)