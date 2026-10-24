"""Record which Twisted advisory code a real Scrapy crawl reaches.

Run with the project interpreter, read-only (``python -B``). The probe starts
a loopback HTTP server, crawls it with Scrapy, and prints one JSON object.
It records three facts for each advisory component:

* whether the module was imported;
* whether a listening TCP port was opened;
* whether the server-side class was instantiated.

``--telnet`` enables the Scrapy default telnet console. It is a positive
control: it proves that the probe can see a listener and a Telnet protocol
object. The msgloom settings module is loaded without the Graph add-on.
"""

from __future__ import annotations

import http.server
import json
import sys
import threading
from typing import Any
from unittest.mock import patch

WATCHED_MODULES = (
    "twisted.mail.imap4",
    "twisted.words.protocols.irc",
    "twisted.words.xish.domish",
    "twisted.conch.telnet",
    "twisted.web.http",
    "twisted.web.server",
)


class _Handler(http.server.BaseHTTPRequestHandler):
    """Serve one small body for any GET request."""

    def do_GET(self) -> None:
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main(argv: list[str]) -> int:
    """Run the crawl and print the observed facts."""
    use_telnet_default = "--telnet" in argv
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"

    import scrapy
    from scrapy.crawler import CrawlerProcess
    from scrapy.settings import Settings
    from twisted.internet import tcp
    from twisted.web import http as twisted_http

    facts: dict[str, Any] = {"listen": [], "http_channels": 0, "items": 0}
    original_listen = tcp.Port.startListening
    original_channel_init = twisted_http.HTTPChannel.__init__

    def record_listen(self: tcp.Port) -> None:
        facts["listen"].append([self.interface, self.port])
        original_listen(self)

    def record_channel(self: twisted_http.HTTPChannel) -> None:
        facts["http_channels"] += 1
        original_channel_init(self)

    class OneSpider(scrapy.Spider):
        name = "a2_f0_probe"

        async def start(self):
            yield scrapy.Request(url, callback=self.parse)

        def parse(self, response):
            facts["items"] += 1
            facts["status"] = response.status

    settings = Settings()
    settings.setmodule("message_ingest.settings", priority="project")
    settings.set("ADDONS", {}, priority="cmdline")
    settings.set("LOG_ENABLED", False, priority="cmdline")
    settings.set("ROBOTSTXT_OBEY", False, priority="cmdline")
    if use_telnet_default:
        settings.set("TELNETCONSOLE_ENABLED", True, priority="cmdline")
        settings.set("TELNETCONSOLE_PORT", [0], priority="cmdline")
    process = CrawlerProcess(settings, install_root_handler=False)
    process.crawl(OneSpider)
    with (
        patch.object(tcp.Port, "startListening", record_listen),
        patch.object(twisted_http.HTTPChannel, "__init__", record_channel),
    ):
        process.start()
    server.shutdown()

    facts["telnetconsole_enabled_setting"] = settings.getbool("TELNETCONSOLE_ENABLED")
    facts["scrapy"] = scrapy.__version__
    import twisted

    facts["twisted"] = twisted.__version__
    facts["modules_imported"] = {name: name in sys.modules for name in WATCHED_MODULES}
    json.dump(facts, sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
