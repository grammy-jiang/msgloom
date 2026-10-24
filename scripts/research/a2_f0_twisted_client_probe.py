"""Record that a Scrapy download uses Twisted's HTTP client response parser.

Run with an interpreter that has Scrapy and Twisted installed. The probe
starts a raw TCP server on ``127.0.0.1`` with an ephemeral port. It sends one
canned response. A real Scrapy crawl downloads that response. The probe
prints one JSON object.

The probe records these facts:

* the class of the download handler that Scrapy chose for ``http``;
* how many times ``twisted.web._newclient.HTTPClientParser`` was built;
* the class names that received response bytes;
* how many times the server-side ``twisted.web.http.HTTPChannel`` was built;
* the response status and the raw header values that the crawl returned.

The probe makes no external connection. It does not use Graph. The
``--mode bare-lf`` option sends a header value that holds a bare LF. It
records how the client parser stores that value. It does not claim that the
behavior is exploitable.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
from typing import Any
from unittest.mock import patch

BODY = b"ok"
HEADER_LINES = {
    "plain": b"X-Plain: one\r\n",
    "bare-lf": b"X-Fold: a\nX-Hidden: b\r\n",
}


def _serve(listener: socket.socket, header_lines: bytes) -> None:
    """Answer each connection with one canned HTTP/1.1 response."""
    while True:
        try:
            conn, _ = listener.accept()
        except OSError:
            return
        with conn:
            conn.settimeout(5)
            try:
                conn.recv(65536)
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\n"
                    + header_lines
                    + b"Content-Length: "
                    + str(len(BODY)).encode()
                    + b"\r\nConnection: close\r\n\r\n"
                    + BODY
                )
            except OSError:
                continue


def main(argv: list[str]) -> int:
    """Run the crawl and print the observed facts."""
    mode = argv[argv.index("--mode") + 1] if "--mode" in argv else "plain"
    if mode not in HEADER_LINES:
        raise SystemExit(f"unknown mode: {mode}")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(5)
    threading.Thread(
        target=_serve, args=(listener, HEADER_LINES[mode]), daemon=True
    ).start()
    url = f"http://127.0.0.1:{listener.getsockname()[1]}/"

    import scrapy
    import twisted
    from scrapy.crawler import CrawlerProcess
    from scrapy.settings import Settings
    from twisted.web import _newclient
    from twisted.web import http as twisted_http

    facts: dict[str, Any] = {
        "mode": mode,
        "parser_built": 0,
        "parser_receivers": [],
        "http_channels": 0,
        "headers": {},
    }
    original_init = _newclient.HTTPClientParser.__init__
    original_data = _newclient.HTTPClientParser.dataReceived
    original_channel = twisted_http.HTTPChannel.__init__

    def record_init(self: Any, request: Any, finisher: Any) -> None:
        facts["parser_built"] += 1
        original_init(self, request, finisher)

    def record_data(self: Any, data: bytes) -> None:
        name = type(self).__name__
        if name not in facts["parser_receivers"]:
            facts["parser_receivers"].append(name)
        original_data(self, data)

    def record_channel(self: Any) -> None:
        facts["http_channels"] += 1
        original_channel(self)

    class OneSpider(scrapy.Spider):
        name = "a2_f0_client_parser_probe"

        async def start(self):
            yield scrapy.Request(url, callback=self.parse)

        def parse(self, response):
            facts["status"] = response.status
            facts["body"] = response.text
            facts["headers"] = {
                key.decode("latin-1"): [v.decode("latin-1") for v in values]
                for key, values in response.headers.items()
            }
            downloader = self.crawler.engine.downloader
            handler = downloader.handlers._get_handler("http")
            facts["handler"] = type(handler).__qualname__

    settings = Settings()
    settings.set("TELNETCONSOLE_ENABLED", False, priority="cmdline")
    settings.set("LOG_ENABLED", False, priority="cmdline")
    settings.set("ROBOTSTXT_OBEY", False, priority="cmdline")
    process = CrawlerProcess(settings, install_root_handler=False)
    process.crawl(OneSpider)
    with (
        patch.object(_newclient.HTTPClientParser, "__init__", record_init),
        patch.object(_newclient.HTTPClientParser, "dataReceived", record_data),
        patch.object(twisted_http.HTTPChannel, "__init__", record_channel),
    ):
        process.start()
    listener.close()
    facts["scrapy"] = scrapy.__version__
    facts["twisted"] = twisted.__version__
    json.dump(facts, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
