import os
import logging
import yt_dlp
from typing import Dict, List

from celery import Task

from common import AppResult
from settings import DATA_DIRECTORY_ROOT

logger = logging.getLogger("cerrrbot")


class YTDownloadTask(Task):
    def run(self, links: List[Dict[str, str]], *args) -> AppResult:
        result = AppResult()
        for link_data in links:
            result_ = yt_download(link_data["url"])
            result.merge(result_)
        return result


options = {
    "username": None,
    "password": None,
    "twofactor": None,
    "client_certificate": None,
    "client_certificate_key": None,
    "client_certificate_password": None,
    "quiet": True,
    "no_warnings": True,
    "simulate": None,
    "outtmpl": os.path.join(DATA_DIRECTORY_ROOT, "%(id)s-%(title)s.%(ext)s"),
    "allowed_extractors": [
        "default"
    ],
    "restrictfilenames": True,
    "ratelimit": None,
    "retries": 10,
    "file_access_retries": 3,
    "concurrent_fragment_downloads": 1,
    "buffersize": 1024,
    "noprogress": True,
    "http_headers": {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "max-age=0",
        "dnt": 1,
        "sec-ch-ua": """Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111""",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
    },
    "proxy": None,
    "postprocessors": [
    {
        "key": "FFmpegConcat",
        "only_multi_video": True,
        "when": "playlist"
    }
    ],
    "geo_bypass": True,
    "geo_bypass_country": None,
    "geo_bypass_ip_block": None,
}


def yt_download(url: str) -> AppResult:
    try:
        downloader = yt_dlp.YoutubeDL(options)
        #downloader.add_progress_hook(my_hook)
        downloader.download([url])
    except Exception as exc:
        logger.exception(exc)
        return AppResult(False, exc)

    return AppResult()