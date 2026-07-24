from typing import Any, Iterable

from aiogram import Router
from celery import Task
from pydantic import BaseModel

from .message_action import CustomMessageAction


class PluginModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    commands_router: Router | None
    tasks: Iterable[type[Task]]
    actions: Iterable[CustomMessageAction | Any]
