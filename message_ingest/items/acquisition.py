"""Provider-independent acquisition item contracts."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RawHttpEvidenceItem:
    """Complete Spider-visible HTTP request/response evidence for a provider."""

    evidence_id: str
    run_id: str | None
    purpose: str
    observed_at: str
    origin: str
    request_fingerprint: str
    request_url: str
    request_method: str
    request_headers: dict[str, list[str]]
    request_body: bytes
    response_url: str | None
    response_status: int | None
    response_headers: dict[str, list[str]]
    response_body: bytes
    response_flags: list[str]
    error_type: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class AcquisitionFailureItem:
    """
    An exhausted acquisition error linked to raw evidence and resource context.
    """

    url: str
    purpose: str
    error_type: str
    error_message: str
    observed_at: str
    context: dict[str, str] = field(default_factory=dict)
    evidence_id: str | None = None
    run_id: str | None = None


__all__ = [
    "AcquisitionFailureItem",
    "RawHttpEvidenceItem",
]
