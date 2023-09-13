from enum import Enum

from aiogram.filters.callback_data import CallbackData
from settings import DEFAULT_CHECK_FOR_NEW_MESSAGES_TIMEOUT, DEFAULT_CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT


class Action(str, Enum):
    cancel = "CANCEL"
    nav_prev = "NAV_PREV"
    nav_next = "NAV_NEXT"
    edit_overwrite = "EDIT_OVERWRITE"
    edit_append = "EDIT_APPEND"


class UserAction(CallbackData, prefix="user"):
    action: Action


CHECK_FOR_NEW_MESSAGES_TIMEOUT = DEFAULT_CHECK_FOR_NEW_MESSAGES_TIMEOUT
CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT = DEFAULT_CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT
CHECK_FOR_NOTIFICATIONS = DEFAULT_CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT

CUSTOM_MESSAGE_MIN_ORDER: int = 100
