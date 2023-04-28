import logging
import os
import re
from typing import Dict, List

import requests
from celery import Task
from common import AppResult, create_directory

logger = logging.getLogger("cerrrbot")


class TelegraphScrapeTask(Task):
    def run(self, links: List[Dict[str, str]], *args) -> AppResult:
        result = AppResult()
        for link_data in links:
            downloader = TelegraphDownloader(link_data["url"])
            downloader.download()
            result.merge(downloader.status)
        return result


class TelegraphDownloader:

    SCHEME = "https"

    def __init__(self, url: str):
        self.status = AppResult()
        self._host = None
        self._url = url
        self._directory_path = None
        self._page_content = None
        self._media_data = None

    def download(self) -> AppResult:
        self._fetch_page_content()
        self._parse_page_media()
        self._prepare_download_media()
        self._download_media()

    def _fetch_page_content(self) -> None:
        try:
            self._page_content = requests.get(self._url).text
        except requests.exceptions.RequestException as exc:
            self._page_content = ""
            logger.error(f"Request error occured: {exc}")

    def _parse_page_media(self):
        re_pattern = re.compile(r'<img src="(?P<file_url>.+?)">')
        self._media_data = re_pattern.findall(self._page_content)

    def _prepare_download_media(self) -> None:
        if not self._media_data:
            self.status = AppResult(False, "Empty media urls")
            return

        if not self._url.startswith("http"):
            self._url = f"{self.SCHEME}://{self._url}"

        url_parts = self._url.split("/")
        self._host = url_parts[2]

        self._setup_directory(url_parts[3])
        self._setup_media_data()

    def _setup_media_data(self) -> None:
        media_data = []
        for url in self._media_data:
            if not url.startswith("http"):
                continue
            file_name = url.split("/")[-1]
            media_data.append((url, file_name))

        self._media_data = media_data

    def _setup_directory(self, dir_name: str) -> None:
        create_result = create_directory(dir_name)
        if not create_result:
            self.status = create_result
            return

        self._directory_path = create_result.data["path"]

    def _download_media(self) -> None:
        if not self.status:
            return

        result = AppResult()
        for media in self._media_data:
            result_ = self._download_file(*media)
            result.merge(result_)

        self.status = result

    def _download_file(self, url: str, file_name: str) -> AppResult:
        file_path = os.path.join(self._directory_path, file_name)
        with open(file_path, "wb") as fd:
            response = requests.get(url)
            fd.write(response.content)

        return AppResult()