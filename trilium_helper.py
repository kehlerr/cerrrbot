from trilium_py.client import ETAPI

from settings import (TRILIUM_NOTE_ID_BOOK_NOTES_ALL,
                      TRILIUM_NOTE_ID_BOOK_ROOT, TRILIUM_NOTE_ID_BOOKMARKS_URL,
                      TRILIUM_TOKEN, TRILIUM_URL)

trilium_client = ETAPI(TRILIUM_URL, TRILIUM_TOKEN)


def add_bookmark_url(url_text: str) -> bool:
    existing_content = trilium_client.get_note_content(TRILIUM_NOTE_ID_BOOKMARKS_URL)
    adding_content = _paragraph(_link(url_text))
    new_content = existing_content+adding_content
    result = trilium_client.update_note_content(TRILIUM_NOTE_ID_BOOKMARKS_URL, new_content)
    return result


def add_note(content: str) -> bool:
    title = content[:10]
    result = trilium_client.create_note(
        parentNoteId=TRILIUM_NOTE_ID_BOOK_NOTES_ALL,
        title=title,
        type="text",
        content=content
    )

    return bool(result.get("note"))


def _link(content: str) -> str:
    return f"""<a href="{content}">{content}</a>"""

def _paragraph(content: str) -> str:
    return f"<p>{content}</p>"


def init_notes():
    existing = trilium_client.search_note(TRILIUM_NOTE_ID_BOOK_ROOT)
    if existing["results"]:
        return

    trilium_client.create_note(
        parentNoteId="root",
        title="[TG] Cerrrbot",
        type="book",
        content="none",
        noteId=TRILIUM_NOTE_ID_BOOK_ROOT
    )

    trilium_client.create_note(
        parentNoteId=TRILIUM_NOTE_ID_BOOK_ROOT,
        title="[TG] Bookmarks URLs",
        type="text",
        content="<hr>",
        noteId=TRILIUM_NOTE_ID_BOOKMARKS_URL
    )

    trilium_client.create_note(
        parentNoteId=TRILIUM_NOTE_ID_BOOK_ROOT,
        title="[TG] All notes",
        type="text",
        content="<hr>",
        noteId=TRILIUM_NOTE_ID_BOOK_NOTES_ALL
    )


init_notes()