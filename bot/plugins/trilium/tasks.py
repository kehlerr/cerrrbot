from celery import Task
from common import AppResult

from .helper import add_bookmark_urls, add_note


class TriliumNote(Task):

    def run(self, _, msgdoc) -> AppResult:
        forward_from_id, title = msgdoc.get_from_chat_data()
        if not forward_from_id:
            forward_from_id, title = msgdoc.get_from_user_data()

        return AppResult(add_note(msgdoc.message_text, forward_from_id, title))


class TriliumBookmark(Task):

    def run(self, links, msgdoc) -> AppResult:
        return AppResult(add_bookmark_urls(msgdoc.message_text, links))
