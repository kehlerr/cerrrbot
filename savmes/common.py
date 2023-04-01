import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aiogram import Bot

from common import AppResult
from settings import DATA_DIRECTORY_ROOT

from .actions import MessageActions

logger = logging.getLogger("cerrrbot")


@dataclass
class SVM_MsgdocInfo:
    action: str = MessageActions.DELETE_NOW
    perform_action_at: int = 0
    reply_action_message_id: Optional[int] = 0
    entities: Optional[List[Dict[str, Any]]] = None
    actions: Dict[str, Any] = field(default_factory=lambda: {})


@dataclass
class SVM_ReplyInfo(SVM_MsgdocInfo):
    popup_text: Optional[str] = None
    need_edit_buttons: Optional[bool] = True

    def __post_init__(self):
        if type(self.actions) in {list, tuple, set}:
            self.actions = {a.code: {} for a in self.actions}


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
