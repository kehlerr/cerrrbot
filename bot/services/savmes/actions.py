import logging

from models import MESSAGE_ACTION_BACK, MESSAGE_ACTION_NONE, MessageAction
from settings import DELETE_TIMEOUT_1, DELETE_TIMEOUT_2, DELETE_TIMEOUT_3

logger = logging.getLogger("cerrrbot")


class MESSAGE_ACTIONS:
    NONE = MESSAGE_ACTION_NONE
    DELETE_REQUEST = MessageAction(
        code="DEL", caption="Delete", order=0, method="delete_request"
    )
    KEEP = MessageAction(code="KEEP", caption="Keep", order=1, method="keep")
    DOWNLOAD = MessageAction(code="DL", caption="Download", order=100, method="download")
    DOWNLOAD_ALL = MessageAction(
        code="DLAL", caption="Download all", order=101, method="download_all"
    )
    TODO = MessageAction(code="NOTO", caption="ToDo", order=5, method="note_todo")
    DELETE_FROM_CHAT = MessageAction(
        code="DFC", caption="Delete from chat", order=1, method="delete_from_chat"
    )
    DELETE_NOW = MessageAction(
        code="DELN", caption="Delete now", order=1, method="delete"
    )
    DELETE_1 = MessageAction(
        code="DEL1",
        caption="Del in 15m",
        order=2,
        method="_delete_after_time",
        method_args={"timeout": DELETE_TIMEOUT_1},
    )
    DELETE_2 = MessageAction(
        code="DEL2",
        caption="Del in 12H",
        order=3,
        method="_delete_after_time",
        method_args={"timeout": DELETE_TIMEOUT_2},
    )
    DELETE_3 = MessageAction(
        code="DEL3",
        caption="Del in 48H",
        order=4,
        method="_delete_after_time",
        method_args={"timeout": DELETE_TIMEOUT_3},
    )
    TASK_STATUS = MessageAction(
        code="TSK_ST", caption="Show status", order=200, method="task_get_status"
    )
    TASK_ABORT = MessageAction(
        code="TSK_AB", caption="Stop", order=201, method="task_abort"
    )
    BACK = MESSAGE_ACTION_BACK

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
        BACK,
    )

    _DEFAULT_CUSTOM_ACTIONS = (
        TASK_STATUS,
        TASK_ABORT,
    )

    BY_CODE = {
        action.code: action for action in (*_DEFAULT_ACTIONS, *_DEFAULT_CUSTOM_ACTIONS)
    }
    CUSTOM_ACTION_BY_CODE = {action.code: action for action in _DEFAULT_CUSTOM_ACTIONS}

    def load_custom_actions(self, actions: list[MessageAction]) -> None:
        for action in actions:
            assert (
                action.code not in self.BY_CODE
            ), f"Duplicated actions can't be loaded: {action.code}"
            self.BY_CODE[action.code] = action
            self.CUSTOM_ACTION_BY_CODE[action.code] = action


MessageActions = MESSAGE_ACTIONS()
