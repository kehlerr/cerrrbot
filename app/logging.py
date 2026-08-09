from enum import StrEnum
import logging
import sys
from typing import Any
from loguru import logger


class LoggingScope(StrEnum):
    APP = "app"
    ALL = "all"


class InterceptHandler(logging.Handler):
    """
    Default handler from examples in loguru documentation.
    See https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame = sys._getframe(0)
        depth = 0
        while frame:
            module_name = frame.f_globals.get("__name__", "")
            if module_name == __name__ or module_name == "logging" or module_name.startswith("logging."):
                frame = frame.f_back
                depth += 1
            else:
                break

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logger(logging_level: str, logging_scope: LoggingScope) -> None:
    # intercept everything at the root logger
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # remove all other handlers from specific loggers
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False

    def scope_filter(record: Any) -> bool:
        if str(logging_scope).lower() == LoggingScope.APP:
            return record["name"].startswith("app.") or record["name"] == "app" or record["name"] == "__main__"

        return True

    # configure loguru
    logger.remove()
    logger.add(
        sys.stdout,
        level=logging_level,
        filter=scope_filter,
        format="<green>{time:MM/DD/YYYY-HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
    )
