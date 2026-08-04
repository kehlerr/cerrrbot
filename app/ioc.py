from typing import AsyncIterable, NewType

from aiogram import Bot
from dishka import Provider, Scope, provide, from_context, AsyncContainer
from pymongo.asynchronous.database import AsyncDatabase
from redis.asyncio import Redis

from app.infrastructure import database as db
from app.infrastructure import make_redis_client
from app.repositories.message_repository import MessageRepository
from app.notifications import NotificationService, NotificationRepository, Notification
from app.savmes import SavmesService, SavmesCacheRepository
from app.actions.action_executors import ActionExecutorRegistry


SavedMessagesRepo = NewType("SavedMessagesRepo", MessageRepository)
NewMessagesRepo = NewType("NewMessagesRepo", MessageRepository)


class AppProvider(Provider):
    # Context dependencies (passed during container creation)
    bot = from_context(provides=Bot, scope=Scope.APP)

    # --- INFRASTRUCTURE  ---

    @provide(scope=Scope.APP)
    async def get_mongo_db(self) -> AsyncIterable[AsyncDatabase]:
        mongo_db = db.get_mongo_db()
        yield mongo_db
        await mongo_db.client.close()

    @provide(scope=Scope.APP)
    async def get_redis(self) -> AsyncIterable[Redis]:
        client = await make_redis_client()
        yield client
        await client.close()

    # --- REPOSITORIES ---

    @provide(scope=Scope.REQUEST)
    def get_saved_messages_repo(self, db: AsyncDatabase) -> SavedMessagesRepo:
        # Resolve collection name dynamically in the provider
        return SavedMessagesRepo(MessageRepository(db, "saved_messages"))

    @provide(scope=Scope.REQUEST)
    def get_new_messages_repo(self, db: AsyncDatabase) -> NewMessagesRepo:
        return NewMessagesRepo(MessageRepository(db, "new_messages"))

    @provide(scope=Scope.REQUEST)
    def get_savmes_cache_repo(self, redis: Redis) -> SavmesCacheRepository:
        return SavmesCacheRepository(redis)

    @provide(scope=Scope.REQUEST)
    def get_notification_repo(self, redis: Redis) -> NotificationRepository:
        return NotificationRepository(redis, Notification)

    # --- SERVICES ---

    @provide(scope=Scope.REQUEST)
    def get_savmes_service(
        self,
        saved_repo: SavedMessagesRepo,
        new_repo: NewMessagesRepo,
        cache_repo: SavmesCacheRepository,
        action_executor_registry: ActionExecutorRegistry
    ) -> SavmesService:
        return SavmesService(saved_repo, new_repo, cache_repo, action_executor_registry)

    @provide(scope=Scope.REQUEST)
    def get_notification_service(self, repo: NotificationRepository) -> NotificationService:
        return NotificationService(repo)


_container: AsyncContainer | None = None


def get_app_container(bot: Bot | None = None) -> AsyncContainer:
    global _container
    if _container is None:
        from dishka import make_async_container
        from app.bot.cerrrbot import CerrrBot
        from app.actions.discovery import discover_actions
        from app.actions.ioc import ActionsProvider

        bot_instance = bot or CerrrBot.create()
        _container = make_async_container(
            AppProvider(),
            ActionsProvider(discover_actions("app.actions.action_executors")),
            context={Bot: bot_instance}
        )
    return _container


def set_app_container(container: AsyncContainer) -> None:
    global _container
    _container = container


