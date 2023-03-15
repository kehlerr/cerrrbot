from .common import MessageActions, SVM_MsgdocInfo


class MessageParser:
    def __init__(self, message_text: str, message_info: SVM_MsgdocInfo):
        self._message_text = message_text
        self._message_info = message_info
        self.actions = {}

    def parse(self) -> None:
        self._parse_urls()
        self._parse_custom_actions()

    def _parse_urls(self) -> None:
        has_url = any(
            e["type"] in {"url", "text_link"} for e in self._message_info.entities
        )
        if has_url:
            self.actions[MessageActions.BOOKMARK.code] = {}

    def _parse_custom_actions(self) -> None:
        for code, action in MessageActions.CUSTOM_ACTION_BY_CODE.items():
            found_data = action.parse(self._message_text)
            if found_data:
                self.actions[code] = {"data": found_data}
