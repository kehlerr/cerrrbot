from typing import Any

from aiogram import Router
from celery import Task
from pydantic import BaseModel

from .message_action import CustomMessageAction


class PluginModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    commands_router: Router | None
    tasks: tuple[type[Task], ...]
    actions: tuple[type[CustomMessageAction] | Any, ...]
