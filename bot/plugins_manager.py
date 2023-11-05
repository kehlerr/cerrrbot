import os
from importlib import import_module

from aiogram import Router
from models import CustomMessageAction, PluginModel
from settings import PLUGINS_DIR_PATH, PLUGINS_MODULE_NAME


class PluginsManager:

    def __init__(self) -> None:
        self._plugins: list[PluginModel] = []
        for plugin_name in os.listdir(PLUGINS_DIR_PATH):
            try:
                plugin_module = import_module(f"{PLUGINS_MODULE_NAME}.{plugin_name}")
            except ModuleNotFoundError:
                continue

            self._plugins.append(self._load_plugin(plugin_module))

    def _load_plugin(self, module) -> PluginModel:
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

        return PluginModel(commands_router=commands_router, tasks=tasks, actions=actions)

    def get_actions(self) -> list[CustomMessageAction]:
        loaded_actions = []
        for plugin in self._plugins:
            loaded_actions.extend(plugin.actions)
        return loaded_actions

    def get_commands_routers(self) -> tuple[Router]:
        return (v.commands_router for v in self._plugins if v.commands_router is not None)

    def get_tasks(self) -> list[Router]:
        loaded_tasks = []
        for plugin in self._plugins:
            loaded_tasks.extend(plugin.tasks)
        return loaded_tasks


plugins_manager = PluginsManager()