class CerrrbotError(Exception):
    """
    Base exception for bot application(s) errors.
    """


class CommandArgsValidationError(CerrrbotError):
    """
    Exception raised when arguments of bot command are invalid.
    """


class EmptyCommandArgsError(CommandArgsValidationError):
    """
    Exception raised when no arguments provided to command where they expected.
    """
