from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActionResult:
    success: bool = True
    message: str | None = None
    popup_text: str | None = None
    message_gone: bool = False
    actions_updated: bool = False
