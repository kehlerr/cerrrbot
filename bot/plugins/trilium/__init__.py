from message_action import CustomMessageAction

from .tasks import TriliumBookmark, TriliumNote


actions = (
    CustomMessageAction(code="CST_NOTE", caption="Note", order=501, method_args={
        "task_name": "plugins.trilium.tasks.TriliumNote",
        "is_instant": True,
        "regex": "*"
    }),
    CustomMessageAction(code="CST_BOOK", caption="Bookmark", order=502, method_args={
        "task_name": "plugins.trilium.tasks.TriliumBookmark",
        "is_instant": True,
        "parse_text_links": True
    }),
)

tasks = (
    TriliumNote,
    TriliumBookmark
)