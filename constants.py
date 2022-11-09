from enum import Enum

from aiogram.filters.callback_data import CallbackData


class Action(str, Enum):
    cancel = "CANCEL"
    nav_prev = "NAV_PREV"
    nav_next = "NAV_NEXT"
    edit_overwrite = "EDIT_OVERWRITE"
    edit_append = "EDIT_APPEND"


class UserAction(CallbackData, prefix="user"):
    action: Action


DEFAULT_PAGE_LIMIT = 30
DEFAULT_TIMEOUT_TO_DELETE_MESSAGES = 15