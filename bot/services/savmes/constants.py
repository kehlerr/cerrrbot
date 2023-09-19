# TG relative constants

EXCLUDE_MESSAGE_FIELDS = {
    "chat": {"first_name", "last_name"},
    "from_user": {"first_name", "last_name", "language_code"},
}


COMMON_GROUP_KEY: str = "media_group_id"

MAX_LOAD_FILE_SIZE: int = 20000000

MESSAGE_DOCUMENT_TTL: int = 2*24*60*60 - 1
