#!/usr/bin/env python3

import asyncio
import logging

from aiogram import Dispatcher, Router
from dishka.integrations.aiogram import setup_dishka

from app import app_settings

from app.bot import handlers_router, make_scheduler, create_periodic_tasks, CheckUserMiddleware
from app.bot.cerrrbot import CerrrBot
from app.bot.commands import load_commands
from app.celery_app import app as _  # noqa: F401
from app.infrastructure.database import check_connection
from app.ioc import get_app_container
from app.plugins_manager import plugins_manager


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("cerrrbot")
    logger.setLevel(app_settings.logging_level)
    log_handler_stream = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(levelname)s][%(asctime)s] %(message)s", "%m/%d/%Y-%H:%M:%S"
    )
    log_handler_stream.setFormatter(formatter)
    logger.addHandler(log_handler_stream)
    return logger



async def main():
    logger = setup_logger()

    logger.info("Starting bot...")

    logger.info("Checking database connection...")
    if await check_connection() is None:
        logger.error("Failed to reach database. Exiting.")
        return
    logger.info("Database is reachable and online.")

    cerrrbot = CerrrBot.create()

    plugins_manager.load()

    main_router = Router()
    main_router.message.middleware(CheckUserMiddleware())
    main_router.callback_query.middleware(CheckUserMiddleware())
    load_commands(main_router)
    main_router.include_router(handlers_router)

    dp = Dispatcher()

    container = get_app_container(cerrrbot)

    scheduler = make_scheduler()
    await create_periodic_tasks(scheduler, cerrrbot, container)
    scheduler.start()

    setup_dishka(container=container, router=main_router)

    dp.include_router(main_router)

    await cerrrbot.start(dp)


if __name__ == "__main__":
    asyncio.run(main())
