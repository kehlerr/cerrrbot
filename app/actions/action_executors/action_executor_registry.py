from logging import getLogger
from typing import Any

from aiogram import Bot

from app.models import ActionResult, MessageAction, MessageDocument
from app.types import ExecutorCode

from ..exceptions import ActionExecutionError, ActionNotFoundError, DuplicateActionExecutorError
from .base import ActionExecutor

logger = getLogger("cerrrbot")


class ActionExecutorRegistry:
    def __init__(self, core_actions: list[ActionExecutor] | None = None) -> None:
        self._actions: dict[ExecutorCode, ActionExecutor] = {}

        if core_actions:
            for action in core_actions:
                self.register(action)

        if self._actions:
            logger.info(f"Actions registry initialized with actions: {self._actions}")

    def register(self, action: ActionExecutor, force_override: bool = False) -> None:
        """
        Registers an action handler. Plugins should call this during their setup phase.
        """
        if (code := action.code) in self._actions and not force_override:
            raise DuplicateActionExecutorError(
                f"Action '{code}' is already registered. "
                "If a plugin needs to override a core action, use force_override=True."
            )

        self._actions[code] = action
        logger.debug(f"Action '{code}' successfully registered.")

    def unregister(self, code: ExecutorCode) -> None:
        """Allows dynamically disabling plugins/actions."""
        if self._actions.pop(code, None):
            logger.debug(f"Action '{code}' unregistered.")

    async def execute(self, action: MessageAction, msgdoc: MessageDocument, bot: Bot, **kwargs: Any) -> ActionResult:

        action_code = action.executor_code

        try:
            handler = self._actions[action_code]
        except KeyError:
            raise ActionNotFoundError(f"Action '{action_code}' is missing in registry. Did you forget to load the plugin?")

        try:
            return await handler.execute(msgdoc, bot, **kwargs)
        except Exception as e:
            # Explicitly catch generic Exceptions here because plugins are untrusted code.
            logger.exception(f"Plugin execution failed for action '{action_code}'")
            raise ActionExecutionError(f"Action '{action_code}' crashed: {str(e)}") from e