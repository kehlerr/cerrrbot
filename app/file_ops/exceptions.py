
from app.exceptions import AppError


class DownloadFileError(AppError):

    detail = "Error occured while downloading file."


class FileVariantError(AppError):

    detail = "Invalid file data variant."


class InvalidStickerSetError(AppError):

    detail = "Invalid sticker set."