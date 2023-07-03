EXCLUDE_MESSAGE_FIELDS = {
    "chat": {"first_name", "last_name"},
    "from_user": {"first_name", "last_name", "language_code"},
}


CUSTOM_MESSAGE_MIN_ORDER: int = 100

COMMON_GROUP_KEY: str = "media_group_id"

MAX_LOAD_FILE_SIZE = 20000000
