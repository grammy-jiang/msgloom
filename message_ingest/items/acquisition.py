"""Provider-independent acquisition item contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RawHttpEvidenceItem:
    """
    Complete Spider-visible HTTP request/response evidence for a provider.

    Keep private transport data out of implicit item logging. ``repr=False``
    changes diagnostics only; pipelines still receive exact evidence fields.
    """

    evidence_id: str
    run_id: str | None
    purpose: str
    observed_at: str
    origin: str
    request_fingerprint: str
    request_url: str = field(repr=False)
    request_method: str
    request_headers: dict[str, list[str]] = field(repr=False)
    request_body: bytes = field(repr=False)
    response_url: str | None = field(repr=False)
    response_status: int | None
    response_headers: dict[str, list[str]] = field(repr=False)
    response_body: bytes = field(repr=False)
    response_flags: list[str]
    error_type: str | None = field(default=None, repr=False)
    error_message: str | None = field(default=None, repr=False)


@dataclass(slots=True)
class AcquisitionFailureItem:
    """
    An exhausted acquisition error linked to raw evidence and resource context.

    URLs, arbitrary exception values, and resource context remain available
    for persistence but are excluded from implicit diagnostic formatting.
    """

    url: str = field(repr=False)
    purpose: str
    error_type: str = field(repr=False)
    error_message: str = field(repr=False)
    observed_at: str
    context: dict[str, str] = field(default_factory=dict, repr=False)
    evidence_id: str | None = None
    run_id: str | None = None


__all__ = [
    "AcquisitionFailureItem",
    "RawHttpEvidenceItem",
]
