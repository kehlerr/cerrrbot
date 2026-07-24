
from app.exceptions import AppError


class ActionError(AppError):

    detail = "Action error occured."


class DuplicateActionLoadedError(AppError):

    detail = "Action has duplicated code."


class DuplicateActionExecutorError(AppError):

    detail = "Action executor has duplicated code."


class ActionNotFoundError(AppError):
    """Raised when trying to execute an unregistered action."""

    detail = "Action not found."


class ActionExecutionError(AppError):
    """Raised when a plugin crashes during execution to prevent orchestrator death."""

    detail = "Error occured on executing action."
