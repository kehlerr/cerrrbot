from celery import Celery

from .savmes_tasks import SavmesTask, TelegraphScrapeTask, TriliumBookmark, TriliumNote

app = Celery(
    "tasks", broker="redis://localhost:6666/0", backend="redis://localhost:6666/1"
)

app.register_task(SavmesTask)
app.register_task(TelegraphScrapeTask)
app.register_task(TriliumNote)
app.register_task(TriliumBookmark)
