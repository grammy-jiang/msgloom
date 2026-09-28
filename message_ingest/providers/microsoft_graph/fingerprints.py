"""
Keep Graph representation choices distinct in the scheduler and HTTP cache.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlsplit

from scrapy.utils.request import fingerprint

from message_ingest.acquisition.source_context import source_catalog_context_digest
from message_ingest.providers.microsoft_graph import GRAPH_HOST

_GRAPH_REPRESENTATION_HEADERS = ("Accept", "Prefer")


class RepresentationAwareRequestFingerprinter:
    """Include source and Graph representation choices in request identity."""

    def __init__(self, source_digest: bytes) -> None:
        """Require an already-derived source/catalog digest."""
        if not source_digest:
            raise ValueError("Graph request fingerprinting requires source context")
        self._source_digest = source_digest

    @classmethod
    def from_crawler(cls, crawler):
        """Build a source-scoped fingerprinter from final crawler settings."""
        digest = source_catalog_context_digest(
            crawler.settings["MSGLOOM_SOURCE_ID"],
            crawler.settings["MSGLOOM_DATABASE_URL"],
        )
        return cls(bytes.fromhex(digest))

    def fingerprint(self, request) -> bytes:
        """
        Include ``Accept`` and ``Prefer`` for Graph; use the native fingerprint
        elsewhere.

        JSON, MIME, and immutable-ID representations of the same URL must not
        share cache or duplicate-filter identity. ``Authorization`` is
        intentionally excluded.
        """
        if urlsplit(request.url).hostname == GRAPH_HOST:
            base = fingerprint(
                request,
                include_headers=_GRAPH_REPRESENTATION_HEADERS,
            )
            return hashlib.sha256(
                b"msgloom-graph-fingerprint-v1\0" + self._source_digest + b"\0" + base
            ).digest()
        return fingerprint(request)


class CalendarDeltaRequestFingerprinter(RepresentationAwareRequestFingerprinter):
    """
    Keep native duplicate filtering separate for each Calendar reset attempt.

    A 410 restarts the same window and may repeat URLs from the old attempt.
    Attempt identity changes only scheduler identity; provider URLs stay opaque.
    Repeated links inside one attempt still hit Scrapy's duplicate filter.
    """

    def fingerprint(self, request) -> bytes:
        base = super().fingerprint(request)
        attempt = request.cb_kwargs.get("reset_count", 0)
        return hashlib.sha256(
            b"msgloom-calendar-delta-attempt-v1\0"
            + str(attempt).encode("ascii")
            + b"\0"
            + base
        ).digest()
