from importlib import import_module
from logging import getLogger
from typing import Any, Iterator

from aiogram import Router
from celery import Task

from app.models import MessageAction, CustomMessageAction
from app.plugins.base import Plugin
from app.settings import PLUGINS_DIR_PATH


logger = getLogger("cerrrbot")


class PluginsManager:
    def __init__(self) -> None:
        self._plugins: list[Plugin] | None = None

    def _ensure_loaded(self) -> None:
        if self._plugins is None:
            self.load()

    @property
    def plugins(self) -> list[Plugin]:
        self._ensure_loaded()
        assert self._plugins is not None
        return self._plugins

    def load(self, force: bool = False) -> None:
        if not force and self._plugins is not None:
            return

        self._plugins = []
        plugins_module_prefix = str(PLUGINS_DIR_PATH).replace("/", ".")
        for module in PLUGINS_DIR_PATH.iterdir():
            module_name = module.name

            if not module.is_dir() or module_name.startswith(".") or module_name.startswith("_"):
                continue

            logger.debug(f"Processing module: {module_name}")

            full_module_name = f"{plugins_module_prefix}.{module_name}"
            try:
                plugin_module = import_module(full_module_name)
            except ModuleNotFoundError as exc:
                logger.debug(f"Module not found: {full_module_name}; skipping...")
                continue

            if plugin := self._load_plugin(plugin_module):
                self._plugins.append(plugin)
                logger.info(f"Plugin loaded: {plugin.name}")

        if not self._plugins:
            logger.info("No plugins loaded")
            return

        self._load_actions()

    def _load_actions(self) -> None:
        from app.actions import MessageActions
        loaded_actions: list[MessageAction | CustomMessageAction] = []
        for plugin in self.plugins:
            loaded_actions.extend(plugin.actions)

        MessageActions.load_custom_actions(loaded_actions)
        logger.info(f"Loaded plugin actions: {loaded_actions}")

    def _load_plugin(self, module: Any) -> Plugin | None:
        plugin_obj = getattr(module, "plugin", None)
        if isinstance(plugin_obj, type) and issubclass(plugin_obj, Plugin):
            plugin_obj = plugin_obj()

        if isinstance(plugin_obj, Plugin):
            if not plugin_obj.enabled:
                logger.info(f"Plugin module {module.__name__} is disabled, skipping...")
                return None
            if not plugin_obj.name:
                plugin_obj.name = module.__name__.split(".")[-1]
            return plugin_obj

        try:
            if not module.ENABLED:
                logger.info(f"Plugin module {module} is not enabled, skipping...")
                return None
        except AttributeError:
            pass

        try:
            return module.plugin
        except AttributeError:
            return None

    def get_commands_routers(self) -> Iterator[Router]:
        return (v.commands_router for v in self.plugins if v.commands_router is not None)

    def load_tasks(self, app) -> None:
        for plugin in self.plugins:
            for task in plugin.tasks:
                app.register_task(task)


plugins_manager = PluginsManager()
