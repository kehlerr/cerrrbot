from app.models import MessageAction
from app.settings import DELETE_TIMEOUT_1, DELETE_TIMEOUT_2, DELETE_TIMEOUT_3
from app.types import ExecutorCode

from .exceptions import DuplicateActionLoadedError


class _MESSAGE_ACTIONS:
    NONE = MessageAction(code="NONE", caption="0", order=0, executor_code=ExecutorCode.NONE)
    DELETE_REQUEST = MessageAction(
        code="DEL",
        caption="Delete",
        order=0,
        executor_code=ExecutorCode.DELETE_REQUEST,
        executor_args={"timeout": 0},
    )
    KEEP = MessageAction(code="KEEP", caption="Keep", order=1, executor_code=ExecutorCode.KEEP)
    DOWNLOAD = MessageAction(code="DL", caption="Download", order=100, executor_code=ExecutorCode.DOWNLOAD)
    DOWNLOAD_ALL = MessageAction(
        code="DLAL", caption="Download all", order=101, executor_code=ExecutorCode.DOWNLOAD_ALL
    )

    DELETE_NOW = MessageAction(
        code="DELN", caption="Delete now", order=1, executor_code=ExecutorCode.DELETE
    )
    DELETE_1 = MessageAction(
        code="DEL1",
        caption="Del in 15m",
        order=2,
        executor_code=ExecutorCode.DELETE_AFTER_TIME,
        executor_args={"timeout": DELETE_TIMEOUT_1},
    )
    DELETE_2 = MessageAction(
        code="DEL2",
        caption="Del in 12H",
        order=3,
        executor_code=ExecutorCode.DELETE_AFTER_TIME,
        executor_args={"timeout": DELETE_TIMEOUT_2},
    )
    DELETE_3 = MessageAction(
        code="DEL3",
        caption="Del in 48H",
        order=4,
        executor_code=ExecutorCode.DELETE_AFTER_TIME,
        executor_args={"timeout": DELETE_TIMEOUT_3},
    )

    TASK_STATUS = MessageAction(
        code="TSK_ST", caption="Show status", order=200, executor_code=ExecutorCode.TASK_GET_STATUS
    )
    TASK_ABORT = MessageAction(
        code="TSK_AB", caption="Stop", order=201, executor_code=ExecutorCode.TASK_ABORT
    )

    MENU_BACK = MessageAction(
        code="MENU_BACK", caption="<- Back", order=5000, executor_code=ExecutorCode.MENU_BACK
    )

    _DEFAULT_ACTIONS = (
        NONE,
        DELETE_REQUEST,
        KEEP,
        DOWNLOAD,
        DOWNLOAD_ALL,
        DELETE_NOW,
        DELETE_1,
        DELETE_2,
        DELETE_3,
        MENU_BACK,
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
            if action.code in self.BY_CODE:
                raise DuplicateActionLoadedError

            self.BY_CODE[action.code] = action
            self.CUSTOM_ACTION_BY_CODE[action.code] = action


MessageActions = _MESSAGE_ACTIONS()
