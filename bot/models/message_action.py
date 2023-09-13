import re
from typing import Any

from pydantic import BaseModel, Field

from constants import CUSTOM_MESSAGE_MIN_ORDER


class MessageAction(BaseModel):
    code: str = Field(min_length=1, max_length=16)
    caption: str
    order: int
    method: str
    method_args: dict[str, Any] = Field(default_factory=dict)

    def __hash__(self):
        return self.order

    def __gt__(self, other):
        return self.order > other.order


class CustomMessageAction(MessageAction):
    caption: str = Field(min_length=1, max_length=32)
    order: int = Field(gt=CUSTOM_MESSAGE_MIN_ORDER)
    method: str = "custom_task"

    def __init__(self, **data):
        data["method_args"]["code"] = data["code"]
        super().__init__(**data)

    def parse(self, text: str, links: list[str]) -> list[str]:
        parsed_data = []
        if self.method_args.get("parse_text_links"):
            parsed_data = list(links)

        regex_pattern = self.method_args.get("regex")
        if not regex_pattern:
            return parsed_data
        elif regex_pattern == "*":
            parsed_data.append(text)
            return parsed_data

        regex = re.compile(regex_pattern, re.IGNORECASE)
        for data in regex.finditer(text):
            parsed = data.group()
            if parsed:
                parsed_data.append(parsed)
        return parsed_data
