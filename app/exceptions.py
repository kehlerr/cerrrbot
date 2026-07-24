from typing import Any


class AppError(Exception):
    """
    Base exception for all domain logic.
    Subclasses should override `detail` property which may be used for human-readable user messages.
    """

    detail: str = "Internal error occured."

    def __init__(
        self,
        log_message: str | None = None,
        detail: str | None = None,
        **context: Any
    ) -> None:
        # Override default user message if provided dynamically
        if detail:
            self.detail = detail

        # If no explicit log message is provided, fallback to the user message
        self.log_message = log_message or self.detail
        self.context = context

        super().__init__(self.log_message)

    def __str__(self) -> str:
        if self.context:
            return f"{self.log_message} | Context: {self.context}"
        return self.log_message



class InvalidSettingError(AppError):
    """
    Exception raised when specified setting value is invalid.
    """

    detail = "Invalid setting value provided."


class CommandArgsValidationError(AppError):
    """
    Exception raised when arguments of bot command are invalid.
    """

    detail = "Invalid command arguments provided."


class EmptyCommandArgsError(CommandArgsValidationError):
    """
    Exception raised when no arguments provided to command where they expected.
    """

    detail = "No command arguments provided."


class InvalidMessageDocumentError(AppError):
    """
    Exception raised when message document is invalid.
    """

    detail = "Invalid message document."
