from celery import Task
from common import AppResult

from .helper import TelegraphDownloader


class TelegraphScrapeTask(Task):
    def run(self, links: list[dict[str, str]], *args) -> AppResult:
        result = AppResult()
        for link_data in links:
            downloader = TelegraphDownloader(link_data["url"])
            downloader.download()
            result.merge(downloader.status)
        return result

