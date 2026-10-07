"""
Keep Graph representation choices distinct in the scheduler and HTTP cache.
"""

from __future__ import annotations

import hashlib

from message_ingest.acquisition.source_context import source_catalog_context_digest
from microsoft_graph import GRAPH_HOST
from microsoft_graph.fingerprints import GraphRequestFingerprinter
from microsoft_graph.request import graph_host


class RepresentationAwareRequestFingerprinter(GraphRequestFingerprinter):
    """Include source and Graph representation choices in request identity."""

    def __init__(self, source_digest: bytes, *, host: str = GRAPH_HOST) -> None:
        """Require an already-derived source/catalog digest."""
        if not source_digest:
            raise ValueError("Graph request fingerprinting requires source context")
        super().__init__(host=host)
        self._source_digest = source_digest

    @classmethod
    def from_crawler(cls, crawler):
        """Build a source-scoped fingerprinter from final crawler settings."""
        digest = source_catalog_context_digest(
            crawler.settings["MSGLOOM_SOURCE_ID"],
            crawler.settings["MSGLOOM_DATABASE_URL"],
        )
        return cls(bytes.fromhex(digest), host=graph_host(crawler))

    def fingerprint(self, request) -> bytes:
        """
        Include ``Accept`` and ``Prefer`` for Graph; use the native fingerprint
        elsewhere.

        JSON, MIME, and immutable-ID representations of the same URL must not
        share cache or duplicate-filter identity. ``Authorization`` is
        intentionally excluded.
        """
        base = super().fingerprint(request)
        if self.is_graph_request(request):
            return hashlib.sha256(
                b"msgloom-graph-fingerprint-v1\0" + self._source_digest + b"\0" + base
            ).digest()
        return base


__all__ = ["RepresentationAwareRequestFingerprinter"]
