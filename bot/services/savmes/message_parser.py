import re

from httpx import URL
from models import ActionsData

from .actions import MessageActions

_URL_PATTERN = "https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)"
URL_REGEX = re.compile(_URL_PATTERN, re.IGNORECASE)


class MessageParser:
    def __init__(self, message_text: str):
        self._message_text = message_text
        self.actions: ActionsData = {}
        self._links: tuple[URL, ...] = ()
        self._init_links()

    def _init_links(self) -> None:
        links = URL_REGEX.findall(self._message_text)
        # if message_info.entities:
        #    links.extend([
        #        e["url"] for e in message_info.entities if e["type"] == "text_link"
        #    ])
        self._links = tuple(URL(link) for link in set(links))

    def parse(self) -> None:
        if not self._message_text and not self._links:
            return
        for code, action in MessageActions.CUSTOM_ACTION_BY_CODE.items():
            found_data = action.parse(self._message_text, self._links)
            if found_data:
                self.actions[code] = {"data": found_data}
