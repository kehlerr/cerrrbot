from celery import Celery

from settings import REDIS_HOST, REDIS_PORT, REDIS_BROKER_DB_IDX, REDIS_BACKEND_DB_IDX

from .savmes_tasks import SavmesTask, TelegraphScrapeTask, TriliumBookmark, TriliumNote

app = Celery(
    "tasks",
    broker=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_BROKER_DB_IDX}",
    backend=f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_BACKEND_DB_IDX}"
)

app.register_task(SavmesTask)
app.register_task(TelegraphScrapeTask)
app.register_task(TriliumNote)
app.register_task(TriliumBookmark)
