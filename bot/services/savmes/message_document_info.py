import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

from .actions import MessageActions

logger = logging.getLogger("cerrrbot")


@dataclass
class SVM_MsgdocInfo:
    action: str = MessageActions.DELETE_NOW
    perform_action_at: int = 0
    reply_action_message_id: Optional[int] = 0
    entities: Optional[list[dict[str, Any]]] = None
    actions: dict[str, Any] = field(default_factory=lambda: {})


@dataclass
class SVM_ReplyInfo(SVM_MsgdocInfo):
    popup_text: Optional[str] = None
    need_edit_buttons: Optional[bool] = True

    def __post_init__(self):
        if type(self.actions) in {list, tuple, set}:
            self.actions = {a.code: {} for a in self.actions}

