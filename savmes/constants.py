import os
import re
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from settings import DELETE_TIMEOUT_1, DELETE_TIMEOUT_2, DELETE_TIMEOUT_3

EXCLUDE_MESSAGE_FIELDS = {
    "chat": {"first_name", "last_name"},
    "from_user": {"first_name", "last_name", "language_code"},
}


CUSTOM_MESSAGE_MIN_ORDER = 500


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


@dataclass(eq=False)
class CustomMessageAction(MessageAction):
    def __post_init__(self, *args, **kwargs):
        if self.order < CUSTOM_MESSAGE_MIN_ORDER:
            raise ValueError(
                f"Action order: {self.order} less than custom message minimal order "
            )

        if "regex" in self.method_args:
            self.method_args["regex"] = re.compile(
                self.method_args["regex"], re.IGNORECASE
            )

        self.method_args["code"] = self.code

    def parse(self, text: str) -> List[str]:
        regex = self.method_args["regex"]
        parsed_groups_data = []
        for data in regex.finditer(text):
            parsed_data = data.groupdict()
            if parsed_data:
                parsed_groups_data.append(parsed_data)
        return parsed_groups_data


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
            500,
            "custom_task",
            {
                "task_name": "SavmesTask",
                "regex": r"(?P<url>https?:\/\/(www\.)?telegra.ph\/([a-zA-Z0-9-_]+)\/?)",
            },
        ]
    ]
)


class MESSAGE_ACTIONS:
    NONE = MessageAction("NONE", "None", 0, "none")
    DELETE_REQUEST = MessageAction("DEL", "Delete", 0, "delete_request")
    SAVE = MessageAction("SAVE", "Save", 1, "save")
    DOWNLOAD_FILE = MessageAction("DL", "Download", 2, "download")
    DOWNLOAD_ALL = MessageAction("DLAL", "Download all", 3, "download_all")
    DOWNLOAD_DELAY = MessageAction("DLDE", "Download delay", 3, "download_delay")
    NOTE = MessageAction("NOTE", "Note", 4, "add_note")
    TODO = MessageAction("NOTO", "ToDo", 5, "note_todo")
    BOOKMARK = MessageAction("AB", "Add bookmark", 6, "note_bookmark_url")
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
        SAVE,
        DOWNLOAD_FILE,
        DOWNLOAD_ALL,
        DOWNLOAD_ALL,
        DOWNLOAD_DELAY,
        NOTE,
        TODO,
        BOOKMARK,
        DELETE_FROM_CHAT,
        DELETE_NOW,
        DELETE_1,
        DELETE_2,
        DELETE_3,
    )

    ACTION_BY_CODE = {action.code: action for action in ALL}
    CUSTOM_ACTION_BY_CODE = {}

    def __init__(self):
        self.CODES = [action.code for action in (*self.ALL, *CustomMessageActions.ALL)]
        self.CUSTOM_ACTION_BY_CODE = {
            action.code: action for action in CustomMessageActions.ALL
        }
        self.ACTION_BY_CODE.update(self.CUSTOM_ACTION_BY_CODE)


MessageActions = MESSAGE_ACTIONS()
