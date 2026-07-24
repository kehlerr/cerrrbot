import os
from logging import getLogger

from aiogram import Bot

from app.settings import DATA_DIRECTORY_ROOT

from .exceptions import DownloadFileError


logger = getLogger("cerrrbot")


def create_directory(directory_name: str) -> str:
    directory_path = get_directory_path(directory_name)

    if not os.path.exists(directory_path):
        os.mkdir(directory_path)

    return directory_path


def get_directory_path(directory_path: str) -> str:
    return os.path.join(DATA_DIRECTORY_ROOT, directory_path)


async def save_file(bot: Bot, file_id: str, file_name: str, dir_name: str) -> None:
    dir_path = os.path.join(DATA_DIRECTORY_ROOT, dir_name)
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)

    file_path = os.path.join(dir_path, file_name)
    try:
        await bot.download(file_id, file_path)
    except Exception as exc:
        raise DownloadFileError("Error occured while downloading file", file_id=file_id, file_path=file_path)
