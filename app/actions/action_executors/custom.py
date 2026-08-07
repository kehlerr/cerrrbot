import asyncio
import logging
from typing import Any, cast

from aiogram import Bot
from celery import signature, states
from celery.contrib.abortable import AbortableAsyncResult as CeleryTaskResult

from app.actions import MessageActions
from app.actions.exceptions import MissingActionDataError
from app.models import ActionResult, MessageDocument, MessageAction
from app.repositories.message_repository import MessageRepository

from app.types import ExecutorCode

from .base import ActionExecutor


logger = logging.getLogger("cerrrbot")


class _TaskActionExecutor(ActionExecutor):

    @classmethod
    def _get_task_status(cls, task_id: str) -> str:
        return CeleryTaskResult(task_id).status



class CustomActionExecutor(_TaskActionExecutor):

    code = ExecutorCode.CUSTOM

    async def _execute_impl(self, msgdoc: MessageDocument, *_: Any, new_repo: MessageRepository, **task_info: Any) -> ActionResult:
        action_code: str = task_info["code"]
        action = MessageActions.BY_CODE[action_code]
        action_data: dict[str, Any] = msgdoc.get_current_menu().get(action_code, {})
        if not action_data:
            raise MissingActionDataError(f"Action data not found for code {action_code}")
        if not (task_id := action_data.get("task_id")):
            return await self._create_task(task_info, action_data["data"], action, msgdoc, repo=new_repo)
        return await self._get_task_reply(task_info, task_id, action, msgdoc, new_repo=new_repo)

    async def _create_task(
        self,
        task_info: dict[str, Any],
        task_args: dict[str, Any],
        action: MessageAction,
        msgdoc: MessageDocument,
        *,
        repo: MessageRepository,
    ) -> ActionResult:
        task_signature = signature(
            task_info["task_name"], args=(task_args,), kwargs={"msgdoc_id": msgdoc.id, "code": action.code}
        )
        if task_info.get("is_instant", False):
            result = cast(ActionResult, await task_signature())
            if result.success:
                await self._update_msgdoc_info(msgdoc, actions_to_del=(action,), new_repo=repo)
            return result

        try:
            result = task_signature.delay()
            task_id = str(result)
            task_status = self._get_task_status(task_id)
        except Exception as exc:
            logger.exception(exc)
            return ActionResult(success=False)

        result_data = {
            "task_id": task_id,
            "additional_caption": f" [{task_status}]",
        }

        await self._update_msgdoc_info(msgdoc, actions_to_add={action: result_data}, new_repo=repo)
        return ActionResult()

    async def _get_task_reply(
        self,
        task_info: dict[str, Any],
        task_id: str,
        action: MessageAction,
        msgdoc: MessageDocument,
        *,
        new_repo: MessageRepository,
    ) -> ActionResult:
        status = self._get_task_status(task_id)
        if status == states.SUCCESS:
            await self._update_msgdoc_info(msgdoc, actions_to_del=(action,), new_repo=new_repo)
            return ActionResult(popup_text=status)

        task_info = {"task_id": task_id}
        actions_data = {
            MessageActions.TASK_STATUS: task_info,
            MessageActions.TASK_ABORT: task_info,
        }
        await self._update_msgdoc_info(msgdoc, new_action=MessageActions.NONE, new_actions_menu=actions_data, new_repo=new_repo)
        return ActionResult(actions_updated=True)


class TaskGetStatusActionExecutor(_TaskActionExecutor):

    code = ExecutorCode.TASK_GET_STATUS

    async def _execute_impl(self, msgdoc: MessageDocument, *_: Any, new_repo: MessageRepository, **task_info: Any) -> ActionResult:
        status = self._get_task_status(task_info["task_id"])
        return ActionResult(popup_text=status)


class TaskAbortActionExecutor(_TaskActionExecutor):

    code = ExecutorCode.TASK_ABORT

    async def _execute_impl(self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository, **task_info: Any) -> ActionResult:
        await asyncio.to_thread(CeleryTaskResult(task_info["task_id"]).abort)
        await self._update_msgdoc_info(msgdoc, actions_to_del=(MessageActions.TASK_ABORT,), new_repo=new_repo)
        return ActionResult(actions_updated=True)
