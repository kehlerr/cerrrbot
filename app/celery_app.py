from typing import Any
from celery import Celery, Task

from app.plugins_manager import plugins_manager
from app.infrastructure import infrastructure_settings


class TestTask(Task):
    def run(self, data, msgdoc):
        print(data)
        return data


class CeleryApp(Celery):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        plugins_manager.load_tasks(self)


app = CeleryApp("tasks", broker=infrastructure_settings.celery_broker, backend=infrastructure_settings.celery_backend)