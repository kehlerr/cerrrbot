class DuplicatedEntryError(Exception):
    """
    Raised if entry with specified key already exists.
    """
    ...


class EntryNotFoundError(Exception):
    """
    Raised if entry with specified not found.
    """
    ...

