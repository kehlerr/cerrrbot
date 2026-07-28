from celery import Celery, Task

from app.infrastructure import infrastructure_settings
from app.plugins_manager import plugins_manager 


class TestTask(Task):
    def run(self, data, msgdoc):
        print(data)
        return data


app = Celery("tasks", broker=infrastructure_settings.celery_broker, backend=infrastructure_settings.celery_backend)

plugins_manager.load_tasks(app)
