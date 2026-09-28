"""Graph representation identity composed from Scrapy's native fingerprint."""

from urllib.parse import urlsplit

from scrapy.utils.request import fingerprint

from microsoft_graph import GRAPH_HOST
from microsoft_graph.request import graph_host

GRAPH_REPRESENTATION_HEADERS = ("Accept", "Prefer")


class GraphRequestFingerprinter:
    """Distinguish Graph representations; exclude credentials from identity."""

    def __init__(self, host: str = GRAPH_HOST) -> None:
        self.host = host

    @classmethod
    def from_crawler(cls, crawler):
        return cls(host=graph_host(crawler))

    def is_graph_request(self, request) -> bool:
        """Return whether representation headers apply to this host."""
        return urlsplit(request.url).hostname == self.host

    def fingerprint(self, request) -> bytes:
        """Preserve native canonical/verbatim URL semantics and header hashing."""
        headers = (
            GRAPH_REPRESENTATION_HEADERS if self.is_graph_request(request) else None
        )
        return fingerprint(request, include_headers=headers)
