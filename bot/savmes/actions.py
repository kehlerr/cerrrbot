import logging
import os
from importlib import import_module

from settings import DELETE_TIMEOUT_1, DELETE_TIMEOUT_2, DELETE_TIMEOUT_3, PLUGINS_MODULE_NAME, PLUGINS_DIR_PATH

from message_action import MessageAction


logger = logging.getLogger(__name__)


class MESSAGE_ACTIONS:
    NONE = MessageAction(
        code="NONE", caption="", order=0, method=""
    )
    DELETE_REQUEST = MessageAction(
        code="DEL", caption="Delete", order=0, method="delete_request"
    )
    KEEP = MessageAction(
        code="KEEP", caption="Keep", order=1, method="keep"
    )
    DOWNLOAD = MessageAction(
        code="DL", caption="Download", order=100, method="download"
    )
    DOWNLOAD_ALL = MessageAction(
        code="DLAL", caption="Download all", order=101, method="download_all"
    )
    TODO = MessageAction(
        code="NOTO", caption="ToDo", order=5, method="note_todo"
    )
    DELETE_FROM_CHAT = MessageAction(
        code="DFC", caption="Delete from chat", order=1, method="delete_from_chat"
    )
    DELETE_NOW = MessageAction(
        code="DELN", caption="Delete now", order=1, method="delete"
    )
    DELETE_1 = MessageAction(
        code="DEL1", caption="Del in 15m", order=2, method="_delete_after_time", method_args={"timeout": DELETE_TIMEOUT_1}
    )
    DELETE_2 = MessageAction(
        code="DEL2", caption="Del in 12H", order=3, method="_delete_after_time", method_args={"timeout": DELETE_TIMEOUT_2}
    )
    DELETE_3 = MessageAction(
        code="DEL3", caption="Del in 48H", order=4, method="_delete_after_time", method_args={"timeout": DELETE_TIMEOUT_3}
    )

    _DEFAULT_ACTIONS = (
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

    BY_CODE = {action.code: action for action in _DEFAULT_ACTIONS}
    CUSTOM_ACTION_BY_CODE = {}

    def __init__(self):
        self._load_custom_actions()
        logger.info("Loaded actions: {}".format(self.BY_CODE))

    def _load_custom_actions(self) -> None:
        loaded_actions = []

        for plugin_name in os.listdir(PLUGINS_DIR_PATH):
            try:
                plugin_module = import_module(f"{PLUGINS_MODULE_NAME}.{plugin_name}")
            except ModuleNotFoundError:
                continue

            try:
                loaded_actions.extend(plugin_module.actions)
            except AttributeError:
                continue

        for action in loaded_actions:
            assert action.code not in self.BY_CODE, f"Duplicated actions can't be loaded: {action.code}"
            self.BY_CODE[action.code] = action
            self.CUSTOM_ACTION_BY_CODE[action.code] = action


MessageActions = MESSAGE_ACTIONS()
