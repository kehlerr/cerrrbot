from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from constants import Action, UserAction


class UserActionKeyboard:
    buttons_data = ()

    def __new__(cls) -> InlineKeyboardMarkup:
        kb_builder = InlineKeyboardBuilder()
        for button_data in cls.buttons_data:
            text, action = button_data
            kb_builder.button(text=text, callback_data=UserAction(action=action))
        return kb_builder.as_markup()


class BackToMainMenuKb(UserActionKeyboard):
    buttons_data = (("Cancel", Action.cancel),)


class NavMenuKb(UserActionKeyboard):
    buttons_data = (
        ("<-", Action.nav_prev),
        ("Cancel", Action.cancel),
        ("->", Action.nav_next),
    )


class NavMenuWithoutNextKb(UserActionKeyboard):
    buttons_data = (
        ("<-", Action.nav_prev),
        ("Cancel", Action.cancel),
    )


class NavMenuWithoutPrevKb(UserActionKeyboard):
    buttons_data = (("Cancel", Action.cancel), ("->", Action.nav_next))


class Keyboards:
    back_to_main_menu = BackToMainMenuKb()
    nav_menu = NavMenuKb()
    nav_menu_without_prev = NavMenuWithoutPrevKb()
    nav_menu_without_next = NavMenuWithoutNextKb()
