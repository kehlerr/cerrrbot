import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Union

from aiogram import Bot

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
from common import AppResult
from settings import DATA_DIRECTORY_ROOT

from .constants import MessageActions

logger = logging.getLogger("cerrrbot")


@dataclass
class CB_MessageInfo:
    action: str = MessageActions.DELETE_NOW
    perform_action_at: int = 0
    reply_action_message_id: int = 0
    entities: Optional[List[Dict[str, Any]]] = None
    actions: Optional[Union[List, Set]] = None


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
