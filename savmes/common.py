import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aiogram import Bot

from common import AppResult
from settings import (
    DATA_DIRECTORY_ROOT,
    DELETE_TIMEOUT_1,
    DELETE_TIMEOUT_2,
    DELETE_TIMEOUT_3,
)

from .constants import CUSTOM_MESSAGE_MIN_ORDER

logger = logging.getLogger("cerrrbot")


@dataclass
class MessageAction:
    code: str
    caption: str
    order: int
    method: str
    method_args: Dict[str, Any] = field(default_factory=lambda: {})

    def __hash__(self):
        return self.order

    def __gt__(self, other):
        return self.order > other.order


class MESSAGE_ACTIONS:
    NONE = MessageAction("NONE", "None", 0, "none")
    DELETE_REQUEST = MessageAction("DEL", "Delete", 0, "delete_request")
    KEEP = MessageAction("KEEP", "Keep", 1, "keep")
    DOWNLOAD_FILE = MessageAction("DL", "Download", 2, "download")
    DOWNLOAD_ALL = MessageAction("DLAL", "Download all", 3, "download_all")
    DOWNLOAD_DELAY = MessageAction("DLDE", "Download delay", 3, "download_delay")
    TODO = MessageAction("NOTO", "ToDo", 5, "note_todo")
    DELETE_FROM_CHAT = MessageAction("DFC", "Delete from chat", 1, "delete_from_chat")
    DELETE_NOW = MessageAction("DELN", "Delete now", 1, "delete")
    DELETE_1 = MessageAction(
        "DEL1", "Del in 15m", 2, "_delete_after_time", {"timeout": DELETE_TIMEOUT_1}
    )
    DELETE_2 = MessageAction(
        "DEL2", "Del in 12H", 3, "_delete_after_time", {"timeout": DELETE_TIMEOUT_2}
    )
    DELETE_3 = MessageAction(
        "DEL3", "Del in 48H", 4, "_delete_after_time", {"timeout": DELETE_TIMEOUT_3}
    )

    ALL = (
        NONE,
        DELETE_REQUEST,
        KEEP,
        DOWNLOAD_FILE,
        DOWNLOAD_ALL,
        DOWNLOAD_ALL,
        DOWNLOAD_DELAY,
        TODO,
        DELETE_FROM_CHAT,
        DELETE_NOW,
        DELETE_1,
        DELETE_2,
        DELETE_3,
    )

    ACTION_BY_CODE = {action.code: action for action in ALL}
    CUSTOM_ACTION_BY_CODE = {}

    def __init__(self, custom_messages):
        self.CODES = [action.code for action in (*self.ALL, *custom_messages)]
        self.CUSTOM_ACTION_BY_CODE = {action.code: action for action in custom_messages}
        self.ACTION_BY_CODE.update(self.CUSTOM_ACTION_BY_CODE)


@dataclass(eq=False)
class CustomMessageAction(MessageAction):
    def __post_init__(self, *args, **kwargs):
        if self.order < CUSTOM_MESSAGE_MIN_ORDER:
            raise ValueError(
                f"Action order: {self.order} less than custom message minimal order "
            )

        self.method_args["code"] = self.code

    def parse(self, text: str, links: List[str]) -> List[str]:
        parsed_data = []
        if self.method_args.get("parse_text_links"):
            parsed_data = list(links)

        regex_pattern = self.method_args.get("regex")
        if not regex_pattern:
            return parsed_data
        elif regex_pattern == "*":
            parsed_data.append(text)
            return parsed_data

        regex = re.compile(regex_pattern, re.IGNORECASE)
        for data in regex.finditer(text):
            parsed = data.groupdict()
            if parsed:
                parsed_data.append(parsed)
        return parsed_data


class CUSTOM_MESSAGE_ACTIONS:
    def __init__(self, actions_list: List[List]):
        actions = []
        for action_info in actions_list:
            actions.append(CustomMessageAction(*action_info))

        self.ALL = actions


CustomMessageActions = CUSTOM_MESSAGE_ACTIONS(
    [
        [
            "TGPH_DL",
            "Download Telegraph",
            600,
            "custom_task",
            {
                "task_name": "SavmesTask",
                "regex": r"(?P<url>https?:\/\/(www\.)?telegra.ph\/([a-zA-Z0-9-_]+)\/?)",
                "is_instant": True,
            },
        ],
        [
            "CST_NOTE",
            "Note",
            500,
            "custom_task",
            {"task_name": "TriliumNote", "regex": "*", "is_instant": True},
        ],
        [
            "CST_BOOKMARK",
            "Bookmark",
            501,
            "custom_task",
            {
                "task_name": "TriliumBookmark",
                "regex": r"^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$",
                "is_instant": True,
                "parse_text_links": True,
            },
        ],
    ]
)


MessageActions = MESSAGE_ACTIONS(CustomMessageActions.ALL)


@dataclass
class SVM_MsgdocInfo:
    action: str = MessageActions.DELETE_NOW
    perform_action_at: int = 0
    reply_action_message_id: Optional[int] = 0
    entities: Optional[List[Dict[str, Any]]] = None
    actions: Dict[str, Any] = field(default_factory=lambda: {})


@dataclass
class SVM_ReplyInfo(SVM_MsgdocInfo):
    popup_text: Optional[str] = None
    need_edit_buttons: Optional[bool] = True

    def __post_init__(self):
        if type(self.actions) in {list, tuple, set}:
            self.actions = {a.code: {} for a in self.actions}


async def save_file(bot: Bot, file_id: str, file_name: str, dir_path: str) -> AppResult:
    if not dir_path:
        dir_path = DATA_DIRECTORY_ROOT

    file_path = os.path.join(dir_path, file_name)
    try:
        await bot.download(file_id, file_path)
    except Exception as exc:
        logger.error(exc)
        return AppResult(False, exc)

    return AppResult()
