
from decouple import config

from settings import SCHEME

TRILIUM_HOST = config("TRILIUM_HOST", default="localhost")
TRILIUM_PORT = config("TRILIUM_PORT", default=8080, cast=int)
TRILIUM_URL = f"{SCHEME}://{TRILIUM_HOST}:{TRILIUM_PORT}"
TRILIUM_TOKEN = config("TRILIUM_TOKEN", default="")
TRILIUM_NOTE_ID_BOOK_ROOT = config("TRILIUM_NOTE_ID_BOOK_ROOT", default= None)
TRILIUM_NOTE_ID_BOOKMARKS_URL = config("TRILIUM_NOTE_ID_BOOKMARKS_URL", default=None)
TRILIUM_NOTE_ID_BOOK_NOTES_ALL = config("TRILIUM_NOTE_ID_BOOK_NOTES_ALL", default=None)
TRILIUM_NOTE_ID_TODO = config("TRILIUM_NOTE_ID_TODO", default=None)