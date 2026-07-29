import re

from httpx import URL

from app.actions import MessageActions
from app.models import ActionsData, MessageAction, MessageEntity

_URL_PATTERN = "https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)"
URL_REGEX = re.compile(_URL_PATTERN, re.IGNORECASE)


class MessageParser:
    def __init__(self, message_text: str | None, entities: list[MessageEntity] | None = None):
        self._message_text = message_text
        self._entities = entities
        self.actions: dict[MessageAction, ActionsData] = {}

    def parse(self) -> None:
        message_links = self._parse_links()

        if not self._message_text and not message_links:
            return

        for action in MessageActions.CUSTOM_ACTION_BY_CODE.values():
            if found_data := action.parse(self._message_text, message_links):
                self.actions[action] = {"data": found_data}

    def _parse_links(self) -> tuple[URL, ...]:
        if self._message_text:
            links = URL_REGEX.findall(self._message_text)
        else:
            links = []

        if self._entities:
           links.extend([
               entity.url for entity in self._entities if entity.type == "text_link"
           ])
        return tuple(URL(link) for link in set(links))
