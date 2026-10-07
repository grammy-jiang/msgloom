"""Select the stored HTTP body that carries one acquisition's evidence."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal

from msgloom.sources.models import SourceReferenceError


@dataclass(frozen=True, slots=True)
class EvidenceRow:
    """Path and integrity fields for the body selected by capture origin.

    The legacy ``response_body_*`` field names also hold inbound or local-gap
    request-body metadata. ``body_kind`` preserves that distinction in saved
    references. Local gap captures have no received HTTP response.
    Headers, URLs, and authentication material are never returned as metadata.
    """

    evidence_id: str
    source_id: str
    observed_at: str
    purpose: str | None
    response_body_sha256: str
    response_body_path: str
    response_body_bytes: int
    body_kind: Literal["request", "response"] = "response"

    @classmethod
    def from_capture(cls, row: sqlite3.Row) -> EvidenceRow:
        """Select the original evidence bytes and validate capture shape."""
        request_method = {"inbound-webhook": "POST", "local-gap": "LOCAL"}.get(
            row["origin"]
        )
        if request_method is not None and (
            row["request_method"] != request_method
            or row["response_url"] is not None
            or row["response_status"] is not None
        ):
            raise SourceReferenceError("request evidence has an invalid HTTP shape")
        kind = "request" if request_method is not None else "response"
        return cls(
            evidence_id=row["evidence_id"],
            source_id=row["source_id"],
            observed_at=row["observed_at"],
            purpose=row["purpose"],
            response_body_sha256=row[f"{kind}_body_sha256"],
            response_body_path=row[f"{kind}_body_path"],
            response_body_bytes=row[f"{kind}_body_bytes"],
            body_kind=kind,
        )
