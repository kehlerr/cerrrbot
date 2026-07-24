from celery import Celery, Task

from app.plugins_manager import plugins_manager
from app.settings import CELERY_BACKEND_DB, CELERY_BROKER_DB, REDIS_HOST, REDIS_PORT


class TestTask(Task):
    def run(self, data, msgdoc):
        print(data)
        return data


app = Celery(
    "tasks",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/{CELERY_BROKER_DB}",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/{CELERY_BACKEND_DB}",
)

plugins_manager.load_tasks(app)
