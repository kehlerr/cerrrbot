#!/usr/bin/env python3

import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.types import StoryAreaTypeUnion
from dishka import make_async_container
from dishka.integrations.aiogram import setup_dishka

from app import app_settings

from app.bot import handlers_router, make_scheduler, create_periodic_tasks, CheckUserMiddleware
from app.bot.cerrrbot import CerrrBot
from app.bot.commands import load_commands
from app.celery_app import app as _  # noqa: F401
from app.actions.discovery import discover_actions
from app.actions.ioc import ActionsProvider
from app.infrastructure.database import check_connection
from app.ioc import AppProvider



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

    main_router = Router()
    main_router.message.middleware(CheckUserMiddleware())
    main_router.callback_query.middleware(CheckUserMiddleware())
    load_commands(main_router)
    main_router.include_router(handlers_router)

    dp = Dispatcher()

    container = make_async_container(
        AppProvider(),
        ActionsProvider(discover_actions("app.actions.action_executors")),
        context={Bot: cerrrbot}
    )

    scheduler = make_scheduler()
    await create_periodic_tasks(scheduler, cerrrbot, container)
    scheduler.start()

    setup_dishka(container=container, router=main_router)

    dp.include_router(main_router)

    await cerrrbot.start(dp)


if __name__ == "__main__":
    asyncio.run(main())
