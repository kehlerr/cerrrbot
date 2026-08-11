#!/usr/bin/env python3

import asyncio
from loguru import logger

from aiogram import Dispatcher, Router
from dishka.integrations.aiogram import setup_dishka

from app.bot import handlers_router, make_scheduler, create_periodic_tasks, CheckUserMiddleware
from app.bot.cerrrbot import CerrrBot
from app.bot.commands import load_commands

from app.celery_app import app as _  # noqa: F401

from app.actions import MessageActions
from app.logging import TableLogger
from app.infrastructure.database import check_connection
from app.ioc import get_app_container
from app.plugins_manager import plugins_manager


async def main():

    logger.info("Starting bot...")

    if not await check_connection():
        return

    cerrrbot = CerrrBot.create()

    plugins_manager.load()

    TableLogger.print_actions_info(
        "Loaded Actions",
        MessageActions.get_actions_log_info() + plugins_manager.get_actions_info()
    )

    main_router = Router()
    main_router.message.middleware(CheckUserMiddleware())
    main_router.callback_query.middleware(CheckUserMiddleware())
    load_commands(main_router)
    main_router.include_router(handlers_router)

    dp = Dispatcher()

    container = get_app_container(cerrrbot)

    await plugins_manager.on_startup(container)

    scheduler = make_scheduler()
    await create_periodic_tasks(scheduler, cerrrbot, container)
    scheduler.start()

    setup_dishka(container=container, router=main_router)

    dp.include_router(main_router)

    await cerrrbot.start(dp)


if __name__ == "__main__":
    asyncio.run(main())
