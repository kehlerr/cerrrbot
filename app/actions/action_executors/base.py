import logging
from typing import Any

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from app.exceptions import AppError
from app.models import ActionResult, MessageDocument
from app.repositories.message_repository import MessageRepository
from app.types import ExecutorCode


logger = logging.getLogger("cerrrbot")


class ActionExecutor:

    code: ExecutorCode

    async def get_related_msgdocs(self, msgdoc: MessageDocument, *, new_repo: MessageRepository) -> list[MessageDocument]:
        if not (media_group_id := msgdoc.media_group_id):
            return []
        return await new_repo.get_many({"media_group_id": media_group_id})

    async def delete_from_chat(self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository) -> None:
        await self.delete_reply_message(msgdoc, bot, new_repo=new_repo)
        try:
            await bot.delete_message(msgdoc.chat.id, msgdoc.message_id)
        except TelegramBadRequest as telegram_bad_request:
            logger.warning(telegram_bad_request)

    async def delete_reply_message(self, msgdoc: MessageDocument, bot: Bot, *, new_repo: MessageRepository) -> None:
        if not (message_id := msgdoc.cb_message_info and msgdoc.cb_message_info.reply_action_message_id):
            logger.info("[%s] There is no reply message to delete", msgdoc.id)
            return

        try:
            await bot.delete_message(msgdoc.chat.id, message_id)
        except TelegramBadRequest as telegram_bad_request:
            logger.warning(telegram_bad_request)

        await self._update_msgdoc_info(msgdoc, new_action=None, new_actions_menu={}, reply_action_message_id=0, new_repo=new_repo)

    async def execute(self, msgdoc: MessageDocument, bot: Bot, **executor_args: Any) -> ActionResult:
        logger.info(f"Executing action: {self.code} on msgdoc: {msgdoc.id}")

        try:
            result = await self._execute_impl(msgdoc, bot, **executor_args)
        except AppError as exc:
            logger.exception(f"Error occured on execting action: {self.code}")
            result = ActionResult(success=False, popup_text=exc.detail, actions_updated=False)

        logger.info(f"Result of performed action: {result}")

        return result

    async def _execute_impl(self, msgdoc: MessageDocument, bot: Bot, **executor_args: Any) -> ActionResult:
        raise NotImplementedError

    async def _update_msgdoc_info(self, msgdoc: MessageDocument, *, new_repo: MessageRepository, **kwargs: Any) -> None:
        msgdoc.update_message_info(**kwargs)
        await new_repo.update_msgdoc(msgdoc)
