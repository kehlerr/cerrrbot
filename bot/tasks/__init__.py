from importlib import import_module

from celery import Celery, Task
from common import get_actions_config
from settings import REDIS_BACKEND_DB_IDX, REDIS_BROKER_DB_IDX, REDIS_HOST, REDIS_PORT


def register_tasks(app: Celery) -> None:
    loaded_modules = {}
    for action_cfg in get_actions_config():
        module_name = action_cfg["module"]
        loaded_modules.setdefault(module_name, import_module(module_name))
        task_cls = getattr(loaded_modules[module_name], action_cfg["task_cls"])
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