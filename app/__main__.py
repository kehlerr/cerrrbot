#!/usr/bin/env python3

import asyncio
from loguru import logger

from aiogram import Dispatcher, Router
from dishka.integrations.aiogram import setup_dishka

from app.bot import handlers_router, make_scheduler, create_periodic_tasks, CheckUserMiddleware
from app.bot.cerrrbot import CerrrBot
from app.bot.commands import load_commands
from app.celery_app import app as _  # noqa: F401
from app.infrastructure.database import check_connection
from app.ioc import get_app_container
from app.plugins_manager import plugins_manager

async def main():

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
