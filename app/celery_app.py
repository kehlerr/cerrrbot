from typing import Any

from celery import Celery as CeleryApp

from app.infrastructure import infrastructure_settings
from app.plugins_manager import plugins_manager

app = CeleryApp("tasks", broker=infrastructure_settings.celery_broker, backend=infrastructure_settings.celery_backend)


@app.on_after_configure.connect
def setup_app_context(sender: CeleryApp, **_: Any) -> None:
    plugins_manager.load_tasks(sender)
