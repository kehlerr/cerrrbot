from celery import Celery

from .savmes_tasks import SavmesTask, TelegraphScrapeTask

app = Celery("tasks", broker="redis://localhost:6666")

app.register_task(SavmesTask)
app.register_task(TelegraphScrapeTask)
