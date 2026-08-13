from collections.abc import Iterator
from importlib import import_module
from typing import Any

from aiogram import Router
from dishka import AsyncContainer, Provider
from loguru import logger

from app.logging import ActionLogInfo, PluginStatusInfo, TableLogger
from app.models import CustomMessageAction, MessageAction
from app.plugins.base import Plugin
from app.settings import PLUGINS_DIR_PATH
from app.types import PluginStatus


class PluginsManager:
    def __init__(self) -> None:
        self._plugins: list[Plugin] | None = None
        self.actions_info: list[ActionLogInfo] = []

    @property
    def plugins(self) -> list[Plugin]:
        self._ensure_loaded()
        assert self._plugins is not None
        return self._plugins

    def _ensure_loaded(self) -> None:
        if self._plugins is None:
            logger.debug("Pugins not initialized.")
            self.load()

    def get_actions_info(self) -> list[ActionLogInfo]:
        return self.actions_info

    def load(self) -> None:
        if self._plugins is not None:
            logger.debug("Pugins already loaded.")
            return

        logger.debug("Loading plugins...")

        self._plugins = []
        plugin_statuses = []

        plugins_module_prefix = str(PLUGINS_DIR_PATH).replace("/", ".")
        for module in PLUGINS_DIR_PATH.iterdir():
            module_name = module.name

            if not module.is_dir() or module_name.startswith(".") or module_name.startswith("_") or "egg-info" in module_name:
                continue

            logger.debug(f"Processing module: {module_name}")

            full_module_name = f"{plugins_module_prefix}.{module_name}"
            try:
                plugin_module = import_module(full_module_name)
            except ModuleNotFoundError:
                logger.debug(f"Module not found: {full_module_name}; skipping...")
                plugin_statuses.append(PluginStatusInfo(name=module_name, status=PluginStatus.FAILED_LOAD, is_active=False))
                continue

            plugin, status = self._load_plugin(plugin_module)
            if plugin:
                self._plugins.append(plugin)
                plugin_statuses.append(PluginStatusInfo(name=plugin.name, status=status, is_active=True))
            else:
                plugin_statuses.append(PluginStatusInfo(name=module_name, status=status, is_active=False))

        if self._plugins:
            self.actions_info = self._load_actions()
        else:
            self.actions_info = []

        TableLogger.print_plugins_info(plugin_statuses)

    def _load_actions(self) -> list[ActionLogInfo]:
        from app.actions import MessageActions

        loaded_actions: list[MessageAction | CustomMessageAction] = []
        action_statuses: list[ActionLogInfo] = []

        for plugin in self.plugins:
            for action in plugin.actions:
                loaded_actions.append(action)
                action_code = action.code if hasattr(action, "code") else str(action)
                action_statuses.append(ActionLogInfo(source_name=plugin.name, action_code=action_code))

        MessageActions.load_custom_actions(loaded_actions)

        return action_statuses

    def _load_plugin(self, module: Any) -> tuple[Plugin | None, PluginStatus]:
        plugin_obj = getattr(module, "plugin", None)
        if isinstance(plugin_obj, type) and issubclass(plugin_obj, Plugin):
            plugin_obj = plugin_obj()

        if isinstance(plugin_obj, Plugin):
            if not plugin_obj.enabled:
                return None, PluginStatus.DISABLED
            if not plugin_obj.name:
                plugin_obj.name = module.__name__.split(".")[-1]
            return plugin_obj, PluginStatus.LOADED

        try:
            if not module.ENABLED:
                return None, PluginStatus.DISABLED
        except AttributeError:
            pass

        try:
            return module.plugin, PluginStatus.LOADED
        except AttributeError:
            return None, PluginStatus.NO_PLUGIN_FOUND

    def get_commands_routers(self) -> Iterator[Router]:
        return (v.commands_router for v in self.plugins if v.commands_router is not None)

    def get_ioc_providers(self) -> Iterator[Provider]:
        for plugin in self.plugins:
            yield from plugin.providers

    def load_tasks(self, app) -> None:
        for plugin in self.plugins:
            for task in plugin.tasks:
                app.register_task(task)

    async def on_startup(self, container: AsyncContainer) -> None:
        for plugin in self.plugins:
            if on_startup_hook := plugin.on_startup_hook:
                await on_startup_hook(container)


plugins_manager = PluginsManager()
