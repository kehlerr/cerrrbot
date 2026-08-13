from app.exceptions import AppError


class RepositoryBaseError(AppError):
    """
    Base exception for all repository logic.
    """

    detail = "Repository internal error occured."


class InsertEntryError(RepositoryBaseError):
    """
    Raised if error occured while inserting entry.
    """

    detail = "Error occured while adding new entry."


class UpdateEntryError(RepositoryBaseError):
    """
    Raised if error occured while updating entry.
    """

    detail = "Error occured while updating existing entry."


class DuplicatedEntryError(RepositoryBaseError):
    """
    Raised if entry with specified key already exists.
    """

    detail = "Entry with specified key already exists."


class EntryNotFoundError(RepositoryBaseError):
    """
    Raised if entry with specified not found.
    """

    detail = "Entry with specified key not found."
