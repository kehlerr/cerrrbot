from typing import Any, Callable, Coroutine

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from dishka import AsyncContainer

from app import app_settings
from app.ioc import get_app_container

from .handlers import perform_message_actions, delete_deprecated_messages, process_notifications


async def create_periodic_tasks(
    scheduler: AsyncIOScheduler,
    bot: Bot,
    app_container: AsyncContainer | None = None
) -> None:
    scheduler.add_job(
        _execute_di_job,
        "interval",
        seconds=app_settings.check_new_messages_cd_period,
        args=[
            app_container,
            perform_message_actions,
        ],
        kwargs={
            "bot": bot
        },
    )

    scheduler.add_job(
        _execute_di_job,
        "interval",
        seconds=app_settings.check_deprecated_messages_cd_period,
        args=[
            app_container,
            delete_deprecated_messages,
        ],
        kwargs={
            "bot": bot
        },
    )

    scheduler.add_job(
        _execute_di_job,
        "interval",
        seconds=app_settings.check_notifications_cd_period,
        args=[
            app_container,
            process_notifications,
            delete_deprecated_messages,
        ],
        kwargs={
            "bot": bot
        },
    )


async def _execute_di_job(
    container: AsyncContainer | None,
    task_func: Callable[..., Coroutine[Any, Any, Any]],
    *args: Any,
    **kwargs: Any
) -> None:
    target_container = container or get_app_container(kwargs.get("bot"))
    async with target_container() as dishka_container:
        await task_func(kwargs["bot"], dishka_container=dishka_container)


def make_scheduler() -> AsyncIOScheduler:
    return AsyncIOScheduler()
