from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from . import savmes
from . import notifications

from settings import (
    CHECK_NOTIFICATIONS_CD_PERIOD,
    CHECK_DEPRECATED_MESSAGES_CD_PERIOD,
    CHECK_NEW_MESSAGES_CD_PERIOD,
)


async def create_background_tasks(bot: Bot) -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        savmes.perform_message_actions,
        "interval",
        (bot,),
        seconds=CHECK_NEW_MESSAGES_CD_PERIOD,
    )
    scheduler.add_job(
        savmes.delete_deprecated_messages,
        "interval",
        (bot,),
        seconds=CHECK_DEPRECATED_MESSAGES_CD_PERIOD
    )
    scheduler.add_job(
        notifications.process_notifications,
        "interval",
        (bot,),
        seconds=CHECK_NOTIFICATIONS_CD_PERIOD,
    )
    scheduler.start()
