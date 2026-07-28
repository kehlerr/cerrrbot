import logging
import os
from importlib import import_module
from typing import Iterator

from aiogram import Router
from celery import Task

from app.models import PluginModel, MessageAction, CustomMessageAction
from app.settings import PLUGINS_DIR_PATH, PLUGINS_MODULE_NAME


logger = logging.getLogger(__name__)


class PluginsManager:
    def __init__(self) -> None:
        self._plugins: list[PluginModel] = []

        for plugin_name in os.listdir(PLUGINS_DIR_PATH):
            try:
                plugin_module = import_module(f"{PLUGINS_MODULE_NAME}.{plugin_name}")
            except ModuleNotFoundError:
                continue

            if plugin := self._load_plugin(plugin_module):
                self._plugins.append(plugin)

        self._load_actions()

        if self._plugins:
            logger.info("Loaded plugins: %s", ", ".join(str(v) for v in self._plugins))
        else:
            logger.info("No plugins loaded")

    def _load_actions(self) -> None:
        from app.actions import MessageActions
        loaded_actions: list[MessageAction | CustomMessageAction] = []
        for plugin in self._plugins:
            loaded_actions.extend(plugin.actions)
        MessageActions.load_custom_actions(loaded_actions)

    def _load_plugin(self, module) -> PluginModel | None:

        try:
            if not module.ENABLED:
                return None
        except AttributeError:
            pass

        try:
            commands_router = module.commands_router
        except AttributeError:
            commands_router = None

        try:
            actions = module.actions
        except AttributeError:
            actions = ()

        try:
            tasks = module.tasks
        except AttributeError:
            tasks = ()

        if not any((tasks, commands_router, actions)):
            return None

        return PluginModel(commands_router=commands_router, tasks=tasks, actions=actions)

    def get_commands_routers(self) -> Iterator[Router]:
        return (v.commands_router for v in self._plugins if v.commands_router is not None)

    def load_tasks(self, app) -> None:
        tasks: list[type[Task]] = []
        for plugin in self._plugins:
            tasks.extend(plugin.tasks)
        for task_cls in tasks:
            app.register_task(task_cls)


plugins_manager = PluginsManager()
