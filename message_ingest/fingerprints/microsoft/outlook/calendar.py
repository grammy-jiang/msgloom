"""Outlook Calendar request identity policies."""

from __future__ import annotations

import hashlib

from message_ingest.fingerprints.microsoft_graph import (
    RepresentationAwareRequestFingerprinter,
)


class CalendarDeltaRequestFingerprinter(RepresentationAwareRequestFingerprinter):
    """Keep native duplicate filtering separate for each Calendar reset attempt.

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


__all__ = ["CalendarDeltaRequestFingerprinter"]
