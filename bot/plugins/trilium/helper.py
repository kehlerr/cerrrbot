import re
from typing import List

import requests
from .settings import (
    TRILIUM_NOTE_ID_BOOK_NOTES_ALL,
    TRILIUM_NOTE_ID_BOOK_ROOT,
    TRILIUM_NOTE_ID_BOOKMARKS_URL,
    TRILIUM_TOKEN,
    TRILIUM_URL,
)
from trilium_py.client import ETAPI

trilium_client = ETAPI(TRILIUM_URL, TRILIUM_TOKEN)

urlregex = (
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)


def add_bookmark_urls(message_text: str, text_links: List[str]) -> bool:
    links = re.findall(urlregex, message_text)
    urls = set(text_links + links)
    existing_content = trilium_client.get_note_content(TRILIUM_NOTE_ID_BOOKMARKS_URL)
    adding_content = _horizontal_line() + _paragraph(
        "<br>".join(_link(url) for url in urls)
    )
    new_content = existing_content + adding_content
    result = trilium_client.update_note_content(
        TRILIUM_NOTE_ID_BOOKMARKS_URL, new_content
    )
    return result


def add_note(message_text: str, forward_from_id: str, forward_from_title: str) -> bool:
    title = message_text[:10]

    content = _transform_message_text(message_text)
    content = "<br>".join(content.split("\n"))

    parent_note_id = TRILIUM_NOTE_ID_BOOK_NOTES_ALL
    if forward_from_id:

        if "-" in forward_from_id:
            forward_from_id = forward_from_id.replace("-", "")
        parent_note_id = create_or_get_parent_note(
            TRILIUM_NOTE_ID_BOOK_NOTES_ALL, forward_from_id, forward_from_title
        )

    result = trilium_client.create_note(
        parentNoteId=parent_note_id or TRILIUM_NOTE_ID_BOOK_NOTES_ALL,
        title=title,
        type="text",
        content=content,
    )

    return bool(result.get("note"))


def _link(content: str) -> str:
    return f"""<a href="{content}">{content}</a>"""


def _paragraph(content: str) -> str:
    return f"<p>{content}</p>"


def _horizontal_line() -> str:
    return "<hr>"


def _transform_message_text(content: str):
    return re.sub(
        urlregex, lambda x: '<a href="{}">{}</a>'.format(x.group(), x.group()), content
    )


def create_or_get_parent_note(
    parent_note_id: str, forward_from_id: str, title: str
) -> str:
    result = trilium_client.get_note(forward_from_id)
    if result.get("status") != requests.codes.NOT_FOUND:
        return forward_from_id

    result = trilium_client.create_note(
        parentNoteId=parent_note_id,
        title=title or forward_from_id,
        type="book",
        content="none",
        noteId=forward_from_id,
    )
    return result and forward_from_id


def init_notes():
    response = trilium_client.get_note(TRILIUM_NOTE_ID_BOOK_ROOT)
    if "noteId" in response:
        return

    trilium_client.create_note(
        parentNoteId="root",
        title="[TG] Cerrrbot",
        type="book",
        content="none",
        noteId=TRILIUM_NOTE_ID_BOOK_ROOT,
    )

    trilium_client.create_note(
        parentNoteId=TRILIUM_NOTE_ID_BOOK_ROOT,
        title="[TG] Bookmarks URLs",
        type="text",
        content="<hr>",
        noteId=TRILIUM_NOTE_ID_BOOKMARKS_URL,
    )

    trilium_client.create_note(
        parentNoteId=TRILIUM_NOTE_ID_BOOK_ROOT,
        title="[TG] All notes",
        type="text",
        content="<hr>",
        noteId=TRILIUM_NOTE_ID_BOOK_NOTES_ALL,
    )


init_notes()
