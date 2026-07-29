
from app.exceptions import AppError


class DownloadFileError(AppError):

    detail = "Error occured while downloading file."


class InvalidStickerSetError(AppError):

    detail = "Invalid sticker set."
