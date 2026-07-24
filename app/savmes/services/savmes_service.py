import logging
from datetime import datetime, timedelta, UTC

from aiogram import Bot
from aiogram.types import Message

from app.actions import MessageActions
from app.exceptions import AppError
from app.models import ActionResult, MessageDocument
from app.repositories.message_repository import MessageRepository
from app.actions.action_executors.action_executor_registry import ActionExecutorRegistry
from app.types import MessageActionCode

from ..repositories.cache import SavmesCacheRepository
from ..constants import MESSAGE_DOCUMENT_TTL
from .content_strategies import (
    ContentStrategy,
    CustomizableContentStrategy,
    cls_strategy_by_content_type,
)


logger = logging.getLogger("cerrrbot")


class SavmesService:

    def __init__(
        self,
        saved_messages_repo: MessageRepository,
        new_messages_repo: MessageRepository,
        cache_repo: SavmesCacheRepository,
        action_executor_registry: ActionExecutorRegistry
    ) -> None:

        self._saved_messages_repo = saved_messages_repo
        self._new_messages_repo = new_messages_repo
        self._cache_repo = cache_repo
        self._action_executor_registry = action_executor_registry

    async def get_msgdoc_by_id(self, msgdoc_id: str) -> MessageDocument | None:
        return await self._new_messages_repo.get_by_id(msgdoc_id)

    async def add_new_message(self, message: Message) -> MessageDocument:
        msgdoc = await self._make_msgdoc_from_message(message)

        content_strategy = self._define_content_strategy(msgdoc.content_type)
        content_strategy.process_new_msgdoc(msgdoc)

        inserted_msgdoc = await self._new_messages_repo.insert(msgdoc)
        logger.info(f"Aded new message with id: [{inserted_msgdoc.id}]")

        return inserted_msgdoc

    @staticmethod
    def _define_content_strategy(content_type: str, action_code: str | None = None) -> type[ContentStrategy]:
        if action_code and action_code in MessageActions.CUSTOM_ACTION_BY_CODE:
            return CustomizableContentStrategy
        return cls_strategy_by_content_type.get(content_type, ContentStrategy)  # type: ignore

    async def set_reply_action_message_id(self, msgdoc: MessageDocument, reply_action_message_id: int) -> None:
        msgdoc.update_message_info(
            new_action=None, reply_action_message_id=reply_action_message_id
        )

        try:
            await self._new_messages_repo.update_msgdoc(msgdoc)
        except AppError:
            logger.exception(f"Failed to set reply action message id: {reply_action_message_id}")

    async def _make_msgdoc_from_message(self, message: Message) -> MessageDocument:
        is_subsequent_in_media_group = await self._cache_repo.is_subsequent_in_media_group(message.media_group_id)
        msgdoc = MessageDocument.from_message(message)
        msgdoc.is_subsequent_in_media_group = is_subsequent_in_media_group
        return msgdoc

    async def execute_message_action(self, msgdoc: MessageDocument, bot: Bot, action_code: MessageActionCode | None = None) -> ActionResult:
        if action_code:
            msgdoc.update_message_info(new_action=MessageActions.BY_CODE[action_code])

        action = msgdoc.get_current_action()
        actions_menu = msgdoc.get_current_menu()

        try:
            action_args = {**action.executor_args, **actions_menu[action.code]}
        except (TypeError, KeyError):
            action_args = {**action.executor_args}

        logger.info(f"Performing action: {action.code} with executor: {action.executor_code} on msgdoc: {msgdoc.id}")

        return await self._action_executor_registry.execute(action, msgdoc, bot, new_repo=self._new_messages_repo, saved_repo=self._saved_messages_repo, **action_args)

    async def get_messages_to_execute_actions(self) -> list[MessageDocument]:
        filter_search = {
            "cb_message_info.perform_action_at": {
                "$lt": int(datetime.now(tz=UTC).timestamp()),
                "$gt": 0,
            }
        }
        messages = await self._new_messages_repo.get_messages_by_filter(filter_search)
        logger.debug("Found {} messages to perform action".format(len(messages)))
        return messages

    async def delete_deprecated_messages(self, bot: Bot) -> None:
        await self._delete_deprecated_messages_from_repo(self._saved_messages_repo, bot)
        await self._delete_deprecated_messages_from_repo(self._new_messages_repo, bot)

    async def _delete_deprecated_messages_from_repo(self, repo: MessageRepository, bot: Bot) -> None:
        filter_search = {
            "date": {
                "$lte": datetime.now(tz=UTC) - timedelta(seconds=MESSAGE_DOCUMENT_TTL),
            }
        }

        msgdocs = await repo.get_messages_by_filter(filter_search)
        logger.debug("Found {} deprecated messages".format(len(msgdocs)))
        for msgdoc in msgdocs:
            await self._action_executor_registry.execute(MessageActions.DELETE_NOW, msgdoc, bot, new_repo=self._new_messages_repo, saved_repo=self._saved_messages_repo)
