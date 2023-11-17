class CerrrbotError(Exception):
    """
    Base exception for bot application(s) errors.
    """


class InvalidSettingError(CerrrbotError):
    """
    Exception raised when specified setting value is invalid.
    """


class CommandArgsValidationError(CerrrbotError):
    """
    Exception raised when arguments of bot command are invalid.
    """


class EmptyCommandArgsError(CommandArgsValidationError):
    """
    Exception raised when no arguments provided to command where they expected.
    """
