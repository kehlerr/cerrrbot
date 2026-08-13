import re
from typing import Any

from httpx import URL
from pydantic import BaseModel, Field

from app import app_settings
from app.types import ExecutorCode, MessageActionCode


class MessageAction(BaseModel):
    code: MessageActionCode = Field(min_length=1, max_length=16)
    caption: str = Field(min_length=1, max_length=32)
    order: int
    executor_code: ExecutorCode
    executor_args: dict[str, Any] = Field(default_factory=dict)

    def __hash__(self):
        return hash(self.order)

    def __gt__(self, other):
        return self.order > other.order

    def parse(self, *args: Any, **kwargs: Any) -> list[str]:
        return []


DEFAULT_NONE_ACTION = MessageAction(code="NONE", caption="0", order=0, executor_code=ExecutorCode.NONE)


class CustomMessageAction(MessageAction):
    order: int = Field(gt=app_settings.custom_message_min_order)
    executor_code: ExecutorCode = ExecutorCode.CUSTOM

    def __init__(self, **data: Any) -> None:
        data.setdefault("executor_args", {})["code"] = data["code"]
        super().__init__(**data)

    def parse(self, text: str, links: tuple[URL]) -> list[str]:
        parsed_data = self._parse_links(links) or []
        regex_pattern = self.executor_args.get("regex")
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
        if not all_links or not self.executor_args.get("parse_links", False):
            return None

        allowed_hosts = self.executor_args.get("allowed_hosts")
        if allowed_hosts is None:
            return [str(url) for url in all_links]

        links = []
        for link in all_links:
            host = link.host and link.host.split("www.")[-1] or None
            if host and host in allowed_hosts:
                links.append(str(link))
        return links
