"""
Keep Graph representation choices distinct in the scheduler and HTTP cache.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from scrapy.utils.request import fingerprint

_GRAPH_HOST = "graph.microsoft.com"
_GRAPH_REPRESENTATION_HEADERS = ("Accept", "Prefer")


class RepresentationAwareRequestFingerprinter:
    """Include Graph representation headers in Scrapy request identity."""

    def fingerprint(self, request) -> bytes:
        """
        Include ``Accept`` and ``Prefer`` for Graph; use the native fingerprint
        elsewhere.

        JSON, MIME, and immutable-ID representations of the same URL must not
        share cache or duplicate-filter identity. ``Authorization`` is
        intentionally excluded.
        """
        if urlsplit(request.url).hostname == _GRAPH_HOST:
            return fingerprint(
                request,
                include_headers=_GRAPH_REPRESENTATION_HEADERS,
            )
        return fingerprint(request)
