import re
from typing import Any

from constants import CUSTOM_MESSAGE_MIN_ORDER
from httpx import URL
from pydantic import BaseModel, Field


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

    def parse(self, *args, **kwargs) -> None:
        return None


class CustomMessageAction(MessageAction):
    caption: str = Field(min_length=1, max_length=32)
    order: int = Field(gt=CUSTOM_MESSAGE_MIN_ORDER)
    method: str = "custom_task"

    def __init__(self, **data):
        data["method_args"]["code"] = data["code"]
        super().__init__(**data)

    def parse(self, text: str, links: tuple[URL]) -> list[str]:
        parsed_data = self._parse_links(links) or []
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

    def _parse_links(self, all_links: tuple[URL]) -> list[str] | None:
        if not all_links or not self.method_args.get("parse_links", False):
            return None

        allowed_hosts = self.method_args.get("allowed_hosts")
        if allowed_hosts is None:
            return [str(url) for url in all_links]

        links = []
        for link in all_links:
            host = link.host and link.host.split("www.")[-1] or None
            if host and host in allowed_hosts:
                links.append(str(link))
        return links


MESSAGE_ACTION_NONE = MessageAction(code="NONE", caption="", order=0, method="")
MESSAGE_ACTION_BACK = MessageAction(
    code="BACK", caption="<- Back", order=5000, method="menu_back"
)
