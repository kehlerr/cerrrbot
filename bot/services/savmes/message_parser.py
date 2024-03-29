from .actions import MessageActions
from .message_document_info import SVM_MsgdocInfo


class MessageParser:
    def __init__(self, message_text: str, message_info: SVM_MsgdocInfo):
        self._message_text = message_text
        self.actions = {}
        self._links = []
        self._init_links(message_info)

    def _init_links(self, message_info: SVM_MsgdocInfo) -> None:
        if not message_info.entities:
            return
        self._links = [
            e["url"] for e in message_info.entities if e["type"] == "text_link"
        ]

    def parse(self) -> None:
        if not self._message_text and not self._links:
            return
        for code, action in MessageActions.CUSTOM_ACTION_BY_CODE.items():
            found_data = action.parse(self._message_text, self._links)
            if found_data:
                self.actions[code] = {"data": found_data}
