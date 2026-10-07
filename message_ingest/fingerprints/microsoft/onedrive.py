"""OneDrive delta request identity policies."""

from __future__ import annotations

import hashlib

from message_ingest.fingerprints.microsoft_graph import (
    RepresentationAwareRequestFingerprinter,
)


class OneDriveDeltaRequestFingerprinter(RepresentationAwareRequestFingerprinter):
    """Separate expired and reset chains while keeping intra-chain deduplication."""

    def fingerprint(self, request) -> bytes:
        """Add only reset-attempt identity around the shared Graph fingerprint."""
        base = super().fingerprint(request)
        attempt = request.cb_kwargs.get("reset_attempt", 0)
        return hashlib.sha256(
            b"msgloom-onedrive-delta-attempt-v1\0"
            + str(attempt).encode("ascii")
            + b"\0"
            + base
        ).digest()


__all__ = ["OneDriveDeltaRequestFingerprinter"]
