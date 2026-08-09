import inspect
from loguru import logger
from importlib import import_module
from pkgutil import walk_packages

from .action_executors import ActionExecutor


def discover_actions(package_name: str) -> list[type[ActionExecutor]]:
    actions: list[type[ActionExecutor]] = []

    try:
        package = import_module(package_name)
    except ImportError as exc:
        logger.exception(exc)
        return actions

    # Walk through all modules in the target package
    prefix = package.__name__ + "."
    for _, module_name, is_pkg in walk_packages(package.__path__, prefix):
        if is_pkg:
            continue

        module = import_module(module_name)

        for _, obj in inspect.getmembers(module, inspect.isclass):
            # 1. Skip classes imported from other modules to avoid duplicates
            if obj.__module__ != module_name:
                continue

            # 2. Skip non-ActionExecutor classes and classes with private names
            if obj == ActionExecutor or not issubclass(obj, ActionExecutor) or obj.__name__.startswith("_"):
                continue

            has_action_executor_code = hasattr(obj, "code") or isinstance(getattr(obj, "action_name", None), property)
            has_execute = hasattr(obj, "execute") and inspect.iscoroutinefunction(obj.execute)

            if has_action_executor_code and has_execute:
                actions.append(obj)

    print(f"Discovered {len(actions)} action executors")

    return actions