#!/usr/bin/env python3

import asyncio
import logging

import models
from aiogram import Bot, Dispatcher, Router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from commands import load_commands
from common import CheckUserMiddleware
from constants import (
    CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT,
    CHECK_FOR_NEW_MESSAGES_TIMEOUT,
    CHECK_FOR_NOTIFICATIONS,
)
from repositories import db
from services import notifications, savmes
from settings import LOGGING_LEVEL, TOKEN

logger = logging.getLogger("cerrrbot")
logger.setLevel(LOGGING_LEVEL)
log_handler_stream = logging.StreamHandler()
formatter = logging.Formatter(
    "[%(levelname)s][%(asctime)s] %(message)s", "%m/%d/%Y-%H:%M:%S"
)
log_handler_stream.setFormatter(formatter)
logger.addHandler(log_handler_stream)



async def create_periodic_tasks(bot: Bot) -> None:
    scheduler.add_job(savmes.perform_message_actions, "interval", (bot,), seconds=CHECK_FOR_NEW_MESSAGES_TIMEOUT)
    scheduler.add_job(savmes.delete_deprecated_messages, "interval", (bot,), seconds=CHECK_FOR_DEPRECATED_MESSAGES_TIMEOUT)
    scheduler.add_job(notifications.process_notifications, "interval", (bot,), seconds=CHECK_FOR_NOTIFICATIONS)
    scheduler.start()

scheduler = AsyncIOScheduler()


async def main():
    logger.info("Checking db...")
    db_info = db.check_connection()
    if db_info:
        logger.info("Got db:{}".format(db_info))
        db.init(models.collections)
    else:
        logger.error("DB is down")

    logger.info("Start bot...")
    bot = Bot(token=TOKEN)
    await create_periodic_tasks(bot)

    main_router = Router()
    main_router.message.middleware(CheckUserMiddleware())
    load_commands(main_router)
    main_router.include_router(savmes.router)

    dp = Dispatcher()
    dp.include_router(main_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception(str(exc))
        exit(-1)
