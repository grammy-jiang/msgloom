"""Run provider-only retry, callback, cache, and core log sanitization crawls."""

import json
import subprocess
import sys

import pytest

RUN = r"""
import importlib.abc
import json
import sys
from pathlib import Path

class NoApplication(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'message_ingest', 'sqlalchemy'}:
            raise ImportError('Standalone crawl imported an application dependency')
sys.meta_path.insert(0, NoApplication())

from scrapy.crawler import CrawlerProcess
from scrapy.extensions.httpcache import FilesystemCacheStorage
from scrapy.http import TextResponse
from twisted.internet.error import ConnectionLost
from microsoft_graph.spiders import GraphCollectionSpider

ROOT = 'https://graph.microsoft.com/v1.0'
NEXT = ROOT + '/contacts?$skiptoken=private-continuation%2fb+%2B'
mode = sys.argv[1]

class UnreadableCacheStorage(FilesystemCacheStorage):
    def retrieve_response(self, spider, request):
        raise OSError('private-cache-exception ' + request.url)

class GraphFixtureHandler:
    lazy = False

    def __init__(self):
        self.attempts = 0

    async def download_request(self, request):
        if request.url == NEXT:
            self.attempts += 1
            if self.attempts == 1 or mode == 'exhausted':
                raise ConnectionLost('private-transport-exception ' + request.url)
            payload = {'value': [{'id': 'private-second-item'}]}
        else:
            payload = {
                'value': [{'id': 'private-first-item'}],
                '@odata.nextLink': NEXT,
            }
        return TextResponse(
            request.url, request=request, body=json.dumps(payload).encode(),
            encoding='utf-8', headers={'Content-Type': 'application/json'},
        )

class Contacts(GraphCollectionSpider):
    name = 'standalone_private_contacts'
    endpoint = '/me/contacts'

    async def start(self):
        async for request in super().start():
            yield request
        if mode == 'start':
            raise RuntimeError('private-start-exception ' + NEXT)

    def resource_to_item(self, resource, response):
        if mode == 'callback' and response.url == NEXT:
            raise RuntimeError('private-callback-exception ' + response.url)
        return super().resource_to_item(resource, response)

process = CrawlerProcess({
    'ADDONS': {'microsoft_graph.addon.MicrosoftGraphAddon': 100},
    'DOWNLOAD_HANDLERS': {'https': GraphFixtureHandler},
    'HTTPCACHE_ENABLED': mode == 'cache',
    'HTTPCACHE_STORAGE': UnreadableCacheStorage,
    'HTTPCACHE_DIR': str(Path(sys.argv[2]).parent / 'cache'),
    'RETRY_TIMES': 1,
    'LOG_LEVEL': 'DEBUG',
    'TELNETCONSOLE_ENABLED': False,
    'REMOTE_CONTROL_ENABLED': False,
})
crawler = process.create_crawler(Contacts)
process.crawl(crawler)
process.start()
Path(sys.argv[2]).write_text(json.dumps(crawler.stats.get_stats(), default=str))
"""


@pytest.mark.parametrize("mode", ["success", "exhausted", "callback", "cache", "start"])
def test_standalone_crawl_hides_continuations_and_exception_text(tmp_path, mode):
    stats_path = tmp_path / "stats.json"
    result = subprocess.run(
        [sys.executable, "-c", RUN, mode, str(stats_path)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = result.stdout + result.stderr
    if result.returncode:
        pytest.fail(output)
    if "private-" in output or "https://graph.microsoft.com" in output:
        pytest.fail("Standalone crawl logs exposed private provider data")
    stats = json.loads(stats_path.read_text())
    if stats.get("retry/count") != 1:
        pytest.fail(f"Expected exactly one native generic retry: {output}")
    if stats.get("retry/reason_count/twisted.internet.error.ConnectionLost") != 1:
        pytest.fail("Safe retry must preserve Scrapy's native exception stats")
    if stats.get("item_scraped_count") != (
        1 if mode in {"exhausted", "callback"} else 2
    ):
        pytest.fail("Standalone retry crawl did not deliver the expected items")
    if "PrivacySafeRetryMiddleware" not in output:
        pytest.fail("Add-on did not install the safe generic retry component")
    if "MicrosoftGraphLogPrivacyExtension" not in output:
        pytest.fail("Add-on did not install the reusable privacy extension")
    if mode == "exhausted" and stats.get("retry/max_reached") != 1:
        pytest.fail("Retry exhaustion must retain native stats")
    if mode == "callback" and stats.get("spider_exceptions/count") != 1:
        pytest.fail("Callback failure must remain visible in native stats")
    if mode == "exhausted" and stats.get("downloader/exception_count") != 2:
        pytest.fail("Exhausted transport attempts must retain native stats")
    if mode == "cache" and (
        stats.get("httpcache/retrieve_error") != 3
        or "Could not read Microsoft Graph cache entry" not in output
        or "error_type=OSError" not in output
    ):
        pytest.fail("Native cache failures must remain visible without private data")
    if mode == "start" and (
        "Error while reading start items and requests: error_type=RuntimeError"
        not in output
    ):
        pytest.fail("Core start failure must remain visible without private data")
