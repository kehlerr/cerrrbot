from celery import Celery, Task
from plugins_manager import plugins_manager
from settings import REDIS_BACKEND_DB_IDX, REDIS_BROKER_DB_IDX, REDIS_HOST, REDIS_PORT


class TestTask(Task):
    def run(self, data, msgdoc):
        print(data)
        return data


app = Celery(
    "tasks",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_BROKER_DB_IDX}",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_BACKEND_DB_IDX}"
)

for task_cls in plugins_manager.get_tasks():
    app.register_task(task_cls)