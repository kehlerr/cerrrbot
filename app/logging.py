import logging
import re
import sys
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from loguru import logger

from app.types import PluginStatus


class LoggingScope(StrEnum):
    APP = "app"
    ALL = "all"


class LogColor(StrEnum):
    BLACK = "black"
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"
    MAGENTA = "magenta"
    CYAN = "cyan"
    WHITE = "white"


class LogFormatter:
    """Helper class to format text for loguru with colors and styles."""

    @staticmethod
    def format_text(
        text: str,
        color: LogColor | str | None = None,
        bg_color: LogColor | str | None = None,
        bold: bool = False,
    ) -> str:
        tags_open: list[str] = []
        tags_close: list[str] = []

        if bold:
            tags_open.append("<b>")
            tags_close.insert(0, "</b>")
        if color:
            tags_open.append(f"<{color}>")
            tags_close.insert(0, f"</{color}>")
        if bg_color:
            bg_tag = str(bg_color).upper()
            tags_open.append(f"<{bg_tag}>")
            tags_close.insert(0, f"</{bg_tag}>")

        open_str = "".join(tags_open)
        close_str = "".join(tags_close)

        return f"{open_str}{text}{close_str}"


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

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logger(logging_level: str, logging_scope: LoggingScope) -> None:
    # intercept everything at the root logger
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # remove all other handlers from specific loggers
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False

    def scope_filter(record: Any) -> bool:
        if str(logging_scope).lower() == LoggingScope.APP:
            record_name = cast(str, record["name"])
            return any((record_name.startswith("app."), record_name == "app", record_name == "__main__"))

        return True

    # configure loguru
    logger.remove()
    logger.add(
        sys.stdout,
        level=logging_level,
        filter=scope_filter,
        format="<green>{time:MM/DD/YYYY-HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        enqueue=True,
    )


@dataclass
class PluginStatusInfo:
    name: str
    status: PluginStatus
    is_active: bool


@dataclass
class ActionLogInfo:
    source_name: str
    action_code: str


class TableLogger:
    @staticmethod
    def _print_table(title: str, columns: list[str], rows: list[list[str]]) -> None:
        if not rows:
            return

        def strip_tags(text: str) -> str:
            return re.sub(r"<[^>]+>", "", text)

        columns_with_idx = ["#"] + columns
        rows_with_idx = [[str(i + 1)] + row for i, row in enumerate(rows)]

        col_widths = [len(c) for c in columns_with_idx]
        for row in rows_with_idx:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(strip_tags(cell)))

        header = " │ ".join(f"{c:<{w}}" for c, w in zip(columns_with_idx, col_widths, strict=True))
        separator = "─┼─".join("─" * w for w in col_widths)

        logger.opt(colors=True).info(LogFormatter.format_text(title, color=LogColor.CYAN, bg_color=LogColor.WHITE, bold=True))
        logger.opt(colors=True).info(LogFormatter.format_text(header, color=LogColor.MAGENTA))
        logger.opt(colors=True).info(LogFormatter.format_text(separator, color=LogColor.MAGENTA))
        for row in rows_with_idx:
            formatted_row = " │ ".join(f"{cell}{' ' * (col_widths[i] - len(strip_tags(cell)))}" for i, cell in enumerate(row))
            logger.opt(colors=True).info(formatted_row)
        logger.info("")  # empty line for spacing

    @staticmethod
    def print_plugins_info(plugins: list[PluginStatusInfo]) -> None:
        plugin_rows = []
        for p in plugins:
            if p.is_active:
                status_formatted = LogFormatter.format_text(str(p.status), color=LogColor.GREEN)
            elif p.status == PluginStatus.DISABLED:
                status_formatted = LogFormatter.format_text(str(p.status), color=LogColor.YELLOW)
            else:
                status_formatted = LogFormatter.format_text(str(p.status), color=LogColor.RED)
            plugin_rows.append([LogFormatter.format_text(p.name, color=LogColor.CYAN), status_formatted])

        if plugin_rows:
            TableLogger._print_table("Plugins info", ["Plugin Name", "Status"], plugin_rows)
        else:
            logger.info("No plugins found")

    @staticmethod
    def print_actions_info(title: str, actions: list[ActionLogInfo]) -> None:
        action_rows = []
        for a in actions:
            action_rows.append(
                [
                    LogFormatter.format_text(a.source_name, color=LogColor.CYAN),
                    LogFormatter.format_text(a.action_code, color=LogColor.GREEN),
                ]
            )

        if action_rows:
            TableLogger._print_table(title, ["Source", "Action Code"], action_rows)
        else:
            logger.info(f"No actions loaded for {title}")
