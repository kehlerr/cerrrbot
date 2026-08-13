from datetime import datetime, timedelta
from typing import Any

from aiogram import Bot
from loguru import logger

from app import app_settings
from app.actions import MessageActions
from app.file_ops import FileDownloader
from app.models import ActionResult, MessageDocument
from app.repositories.message_repository import MessageRepository
from app.types import ContentType, ExecutorCode

from .base import ActionExecutor


class KeepActionExecutor(ActionExecutor):
    code = ExecutorCode.KEEP

    async def _execute_impl(
        self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository, saved_repo: MessageRepository, **_: Any
    ) -> ActionResult:
        msgdoc.update_message_info(new_actions_menu={})

        await self._move_msgdoc_to_saved(msgdoc, new_repo=new_repo, saved_repo=saved_repo)
        await self.delete_reply_message(msgdoc, bot, new_repo=new_repo)

        return ActionResult()

    async def _move_msgdoc_to_saved(
        self, msgdoc: MessageDocument, *, new_repo: MessageRepository, saved_repo: MessageRepository
    ) -> None:

        await new_repo.delete_msgdoc(msgdoc)

        msgdoc = await saved_repo.insert(msgdoc)

        logger.info(f"Moved message to saved:: [{msgdoc}]")


class MenuBackActionExecutor(ActionExecutor):
    code = ExecutorCode.MENU_BACK

    async def _execute_impl(self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository, **_: Any) -> ActionResult:
        await self._update_msgdoc_info(msgdoc, new_action=MessageActions.NONE, new_actions_menu={}, new_repo=new_repo)
        return ActionResult(actions_updated=True)


class DeleteRequestActionExecutor(ActionExecutor):
    code = ExecutorCode.DELETE_REQUEST

    async def _execute_impl(self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository, **_: Any) -> ActionResult:
        actions_data = {
            MessageActions.DELETE_1: {"timeout": app_settings.delete_timeout_1},
            MessageActions.DELETE_2: {"timeout": app_settings.delete_timeout_2},
            MessageActions.DELETE_3: {"timeout": app_settings.delete_timeout_3},
            MessageActions.DELETE_NOW: {},
        }

        await self._update_msgdoc_info(
            msgdoc,
            new_action=MessageActions.DELETE_REQUEST,
            new_actions_menu=actions_data,
            new_perform_action_at=0,
            new_repo=new_repo,
        )
        return ActionResult(actions_updated=True)


class DeleteActionExecutor(ActionExecutor):
    code = ExecutorCode.DELETE

    async def _execute_impl(
        self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository, **kwargs: Any
    ) -> ActionResult:
        for related_msgdoc in await self.get_related_msgdocs(msgdoc, new_repo=new_repo):
            await self._delete_one(related_msgdoc, bot, new_repo=new_repo)

        await self._delete_one(msgdoc, bot, new_repo=new_repo, **kwargs)
        return ActionResult(message_gone=True)

    async def _delete_one(self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository, **kwargs: Any) -> None:
        await self.delete_from_chat(msgdoc, bot, new_repo=new_repo, **kwargs)
        await new_repo.delete_msgdoc(msgdoc)


class DeleteAfterTimeActionExecutor(ActionExecutor):
    code = ExecutorCode.DELETE_AFTER_TIME

    async def _execute_impl(
        self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository, **executor_args: Any
    ) -> ActionResult:
        timeout = executor_args["timeout"]

        delete_after = datetime.now() + timedelta(seconds=timeout)
        logger.info(f"[{msgdoc.id}] Message will be deleted after: {delete_after}")

        await self._update_msgdoc_info(msgdoc, new_action=MessageActions.DELETE_NOW, new_ttl=timeout, new_repo=new_repo)
        return ActionResult(popup_text=f"Message will be deleted after: {delete_after.strftime('%Y-%m-%d %H:%M:%S')}")


class DownloadActionExecutor(ActionExecutor):
    code = ExecutorCode.DOWNLOAD

    async def _execute_impl(self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository, **_: Any) -> ActionResult:

        await FileDownloader.download_one(msgdoc, bot)

        await self._update_msgdoc_info(
            msgdoc, actions_to_del=(MessageActions.DOWNLOAD, MessageActions.DOWNLOAD_ALL), new_repo=new_repo
        )
        return ActionResult(actions_updated=True)


class DownloadAllActionExecutor(ActionExecutor):
    code = ExecutorCode.DOWNLOAD_ALL

    async def _execute_impl(self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository, **_: Any) -> ActionResult:

        if msgdoc.content_type == ContentType.STICKER:
            msgdocs = [msgdoc]
        else:
            msgdocs = await self.get_related_msgdocs(msgdoc, new_repo=new_repo)

        await FileDownloader.download_many(msgdocs, bot)

        await self._update_msgdoc_info(
            msgdoc, actions_to_del=(MessageActions.DOWNLOAD, MessageActions.DOWNLOAD_ALL), new_repo=new_repo
        )
        return ActionResult(actions_updated=True)
