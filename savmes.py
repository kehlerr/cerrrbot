from typing import Any, Dict

from aiogram import Bot

import db_utils as db
from common import AppResult


async def add_new_message(message: Dict[str, Any]) -> AppResult:
    return db.NewMessagesCollection.add_document(message)


async def process_saved_message():
    pass


async def download_file(file_id: str, bot: Bot) -> AppResult:
    file_ = await bot.get_file(file_id)
    file_path = file_.file_path

    base_file_name = file_path.split("/")[-1]
    unique_file_name = file_.file_unique_id
    dest_file_name = f"{base_file_name}_{unique_file_name}"

    try:
        await bot.download(file_id, destination=dest_file_name, timeout=60)
    except Exception as exc:
        return AppResult(False, exc)

    return AppResult(True)
