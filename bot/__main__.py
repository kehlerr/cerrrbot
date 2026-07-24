import logging

from aiohttp import web

import models
from tg import Bot
from celery_app import app as _  # noqa: F401
from repositories import db
from settings import LOGGING_LEVEL, WEBHOOK_APP_HOST, WEBHOOK_APP_PORT


def main():
    logger = setup_logger()
    logger.info("Checking db...")
    db_info = db.check_connection()
    if db_info:
        logger.info("Got db:{}".format(db_info))
        db.init(models.collections)
    else:
        logger.error("DB is down")

    bot = Bot.create()
    bot.setup()
    web.run_app(bot.web_app, host=WEBHOOK_APP_HOST, port=WEBHOOK_APP_PORT)


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("cerrrbot")
    logger.setLevel(LOGGING_LEVEL)
    log_handler_stream = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(levelname)s][%(asctime)s] %(message)s", "%m/%d/%Y-%H:%M:%S"
    )
    log_handler_stream.setFormatter(formatter)
    logger.addHandler(log_handler_stream)
    return logger


main()