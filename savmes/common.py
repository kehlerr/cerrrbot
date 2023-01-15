import logging
import os
from dataclasses import dataclass
from typing import Optional

from aiogram import Bot
from aiogram.types import ContentType

from common import AppResult
from settings import DATA_DIRECTORY_ROOT

from .constants import MessageActions

logger = logging.getLogger("cerrrbot")


@dataclass
class CB_MessageInfo:
    action: str = MessageActions.DELETE_NOW
    perform_action_at: int = 0
    common_group_key: Optional[str] = None
    content_type: str = ContentType.TEXT
    url_text: Optional[str] = None


async def save_file(bot: Bot, file_id: str, file_name: str, dir_path: str) -> AppResult:
    if not dir_path:
        dir_path = DATA_DIRECTORY_ROOT

    file_path = os.path.join(dir_path, file_name)
    try:
        await bot.download(file_id, file_path)
    except Exception as exc:
        logger.error(exc)
        return AppResult(False, exc)

    return AppResult()
