import asyncio

from celery import Task
from common import AppResult

from notifications import Notificaiton, push_message_notification

from .helper import TelegraphDownloader


class TelegraphScrapeTask(Task):
    def run(self, links: list[dict[str, str]], *args) -> AppResult:
        result = AppResult()
        for link in links:
            downloader = TelegraphDownloader(link)
            downloader.download()
            result.merge(downloader.status)
        asyncio.run(push_message_notification(Notificaiton(text="TG DL finished")))
        return result

