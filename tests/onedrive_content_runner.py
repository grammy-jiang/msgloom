"""Run the real OneDrive content stack with a local authorization sentinel."""

import json
import sys
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlsplit

from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from message_ingest.items.acquisition import AcquisitionFailureItem
from message_ingest.spiders.microsoft.onedrive.content import (
    MicrosoftOneDriveContentSpider,
)


class AuthorizationSentinel:
    """Authenticate only the local Graph host; native redirect owns removal."""

    def process_request(self, request):
        if urlsplit(request.url).hostname == "localhost":
            request.headers["Authorization"] = "Bearer ONE-DRIVE-AUTH-SENTINEL"


def main():
    settings = get_project_settings()
    settings.setdict(json.loads(sys.argv[1]), priority="cmdline")
    middleware = settings.getdict("DOWNLOADER_MIDDLEWARES")
    middleware[AuthorizationSentinel] = 940
    settings.set("DOWNLOADER_MIDDLEWARES", middleware, priority="cmdline")
    process = CrawlerProcess(settings)
    crawler = process.create_crawler(MicrosoftOneDriveContentSpider)
    failures = []

    def capture(item, **kwargs):
        if isinstance(item, AcquisitionFailureItem):
            failures.append(asdict(item))

    crawler.signals.connect(capture, signal=signals.item_scraped, weak=False)
    process.crawl(crawler, item_ids=json.dumps(["file/+%2F"]))
    process.start()
    Path(sys.argv[2]).write_text(json.dumps(failures))
    spider = crawler.spider
    failed = (
        process.bootstrap_failed
        or not isinstance(spider, MicrosoftOneDriveContentSpider)
        or spider.run_failed
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
