"""Run standalone Graph acquisition through native Scrapy and feed exports."""

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import pytest


@pytest.fixture
def graph_server():
    seen = []
    root = ""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def do_GET(self):
            seen.append((self.path, self.headers.get("client-request-id")))
            if len(seen) == 1:
                status, payload = 429, {"error": {"code": "TooManyRequests"}}
            elif self.path in {"/v1.0/me/contacts", "/v1.0/me/messages"}:
                status, payload = (
                    200,
                    {
                        "value": [{"id": "first"}],
                        "@odata.nextLink": root + "/page?cursor=a%2Fb+%2B&x=2&x=1",
                    },
                )
            else:
                status, payload = 200, {"value": [{"id": "second"}]}
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Retry-After", "0")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    root = f"http://127.0.0.1:{server.server_port}/v1.0"
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield root, seen
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


@pytest.mark.parametrize("resource", ["contacts", "messages"])
def test_collection_crawl_retries_paginates_and_exports_without_pipeline(
    tmp_path,
    graph_server,
    resource,
):
    root, seen = graph_server
    feed = tmp_path / f"{resource}.json"
    report = tmp_path / "stats.json"
    code = """
import json
import sys
from pathlib import Path
from scrapy.crawler import CrawlerProcess
from microsoft_graph.items.outlook import OutlookMessageItem
from microsoft_graph.spiders import GraphCollectionSpider

class Contacts(GraphCollectionSpider):
    name = "standalone_contacts"
    endpoint = "/me/contacts"
    graph_permissions = ("Contacts.Read",)

class Messages(GraphCollectionSpider):
    name = "standalone_messages"
    endpoint = "/me/messages"
    graph_permissions = ("Mail.Read",)

    def resource_to_item(self, resource, response):
        return OutlookMessageItem.from_graph(resource)

process = CrawlerProcess({
    "ADDONS": {"microsoft_graph.addon.MicrosoftGraphAddon": 100},
    "MS_GRAPH_SERVICE_ROOT": sys.argv[1],
    "FEEDS": {sys.argv[2]: {"format": "json", "overwrite": True}},
    "TELNETCONSOLE_ENABLED": False,
    "REMOTE_CONTROL_ENABLED": False,
    "LOG_ENABLED": False,
})
crawler = process.create_crawler(Messages if sys.argv[4] == "messages" else Contacts)
process.crawl(crawler)
process.start()
Path(sys.argv[3]).write_text(json.dumps(crawler.stats.get_stats(), default=str))
"""
    result = subprocess.run(
        [sys.executable, "-c", code, root, str(feed), str(report), resource],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode:
        pytest.fail(result.stderr)
    items = json.loads(feed.read_text())
    field = "raw" if resource == "messages" else "resource"
    if [item[field]["id"] for item in items] != ["first", "second"]:
        pytest.fail("Standalone crawler must feed-export every default item")
    if resource == "messages" and [item["message_id"] for item in items] != [
        "first",
        "second",
    ]:
        pytest.fail("Default Outlook Items must export their provider projection")
    if [path for path, _ in seen] != [
        f"/v1.0/me/{resource}",
        f"/v1.0/me/{resource}",
        "/v1.0/page?cursor=a%2Fb+%2B&x=2&x=1",
    ]:
        pytest.fail(f"Unexpected provider requests: {seen}")
    if len({identifier for _, identifier in seen}) != 3:
        pytest.fail("Retry and continuation attempts need distinct correlation IDs")
    stats = json.loads(report.read_text())
    if stats.get("microsoft_graph/graph_error_retry/count") != 1:
        pytest.fail("Graph middleware must retry before native HTTP error handling")
    if stats.get("item_scraped_count") != 2 or stats.get("finish_reason") != "finished":
        pytest.fail("Standalone acquisition must finish with two scraped items")
