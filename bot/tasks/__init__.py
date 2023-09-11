import os
from importlib import import_module

from celery import Celery, Task

from settings import (
    REDIS_BACKEND_DB_IDX,
    REDIS_BROKER_DB_IDX,
    REDIS_HOST,
    REDIS_PORT,
    PLUGINS_MODULE_NAME,
    PLUGINS_DIR_PATH
)


def register_tasks(app: Celery) -> None:
    loaded_tasks = []
    for plugin_name in os.listdir(PLUGINS_DIR_PATH):
        try:
            plugin_module = import_module(f"{PLUGINS_MODULE_NAME}.{plugin_name}")
        except ModuleNotFoundError:
            continue

        try:
            loaded_tasks.extend(plugin_module.tasks)
        except AttributeError:
            continue

    for task_cls in loaded_tasks:
        app.register_task(task_cls)


class TestTask(Task):
    def run(self, data, msgdoc):
        print(data)
        return data

app = Celery(
    "tasks",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_BROKER_DB_IDX}",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_BACKEND_DB_IDX}"
)

register_tasks(app)