"""Durable evidence adapter for the reviewed Phase 1 AI runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from msgloom.ai_evidence.codec_common import EvidenceCodecError
from msgloom.ai_evidence.codecs import (
    AI_EVIDENCE_CODECS,
    AI_EVIDENCE_SCHEMAS,
    RequestEvidenceCodec,
    TerminalEvidenceCodec,
    TraceEvidenceCodec,
)
from msgloom.ai_evidence.models import RequestEvidence, TerminalEvidence, TraceEvidence

if TYPE_CHECKING:
    from msgloom.ai_evidence.session import (
        DuplicateAttemptError,
        EvidenceSession,
        EvidenceSessionError,
        EvidenceStateError,
        PersistenceTraceSink,
    )

_SESSION_EXPORTS = frozenset(
    {
        "DuplicateAttemptError",
        "EvidenceSession",
        "EvidenceSessionError",
        "EvidenceStateError",
        "PersistenceTraceSink",
    }
)


def __getattr__(name: str) -> object:
    """Load persistence-backed session symbols only when explicitly requested."""
    if name not in _SESSION_EXPORTS:
        raise AttributeError(name)
    from msgloom.ai_evidence import session

    return getattr(session, name)


__all__ = [
    "AI_EVIDENCE_CODECS",
    "AI_EVIDENCE_SCHEMAS",
    "DuplicateAttemptError",
    "EvidenceCodecError",
    "EvidenceSession",
    "EvidenceSessionError",
    "EvidenceStateError",
    "PersistenceTraceSink",
    "RequestEvidence",
    "RequestEvidenceCodec",
    "TerminalEvidence",
    "TerminalEvidenceCodec",
    "TraceEvidence",
    "TraceEvidenceCodec",
]
