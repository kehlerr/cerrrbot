
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from common import get_actions_config
from settings import DELETE_TIMEOUT_1, DELETE_TIMEOUT_2, DELETE_TIMEOUT_3

from .constants import CUSTOM_MESSAGE_MIN_ORDER


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
    DOWNLOAD = MessageAction("DL", "Download", 2, "download")
    DOWNLOAD_ALL = MessageAction("DLAL", "Download all", 3, "download_all")
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
        DOWNLOAD,
        DOWNLOAD_ALL,
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
    method: str = "custom_task"

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
            parsed = data.group()
            if parsed:
                parsed_data.append(parsed)
        return parsed_data


class CUSTOM_MESSAGE_ACTIONS:
    def __init__(self):
        self.ALL = []
        self._load_actions()

    def _load_actions(self) -> None:
        actions = []
        for action_cfg in get_actions_config():
            action_def = action_cfg["def"]
            action = CustomMessageAction(
                action_def["code"],
                action_def["caption"],
                action_def["order"],
            )
            method_args = action_def.get("args")
            if method_args:
                try:
                    regex = method_args["regex"]
                    method_args["regex"] = regex.replace("\\\\", "\\")
                except KeyError:
                    pass
                method_args["code"] = action_def["code"]
                method_args["task_name"] = ".".join((action_cfg["module"], action_cfg['task_cls']))
                action.method_args = method_args
            actions.append(action)
        self.ALL = actions


CustomMessageActions = CUSTOM_MESSAGE_ACTIONS()
MessageActions = MESSAGE_ACTIONS(CustomMessageActions.ALL)
