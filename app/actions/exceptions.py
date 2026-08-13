from app.exceptions import AppError


class ActionError(AppError):
    detail = "Action error occured."


class DuplicateActionLoadedError(ActionError):
    detail = "Action has duplicated code."


class DuplicateActionExecutorError(ActionError):
    detail = "Action executor has duplicated code."


class ActionNotFoundError(ActionError):
    """Raised when trying to execute an unregistered action."""

    detail = "Action not found."


class ActionExecutionError(ActionError):
    """Raised when a plugin crashes during execution to prevent orchestrator death."""

    detail = "Error occured on executing action."


class MissingActionDataError(ActionError):
    """Raised when action data is missing from a message document."""

    detail = "Action data not found."
