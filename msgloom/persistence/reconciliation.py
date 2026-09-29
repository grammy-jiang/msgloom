"""Typed contracts for explicit external-effect reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from msgloom.contracts import (
    ClaimKind,
    ClaimToken,
    ExternalEffectState,
    ResultRef,
    TerminalStatus,
)

_MAX_IDENTITY = 128
_MAX_EVIDENCE = 32
_MAX_HISTORY = 100
_DECISIONS = frozenset(
    {
        ExternalEffectState.UNKNOWN,
        ExternalEffectState.ACCEPTED,
        ExternalEffectState.CONFIRMED,
        ExternalEffectState.REJECTED,
    }
)


@dataclass(frozen=True, slots=True)
class ReconciliationIdentity:
    """Identify one immutable caller-owned reconciliation decision."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("reconciliation identity must be non-empty text")
        if len(self.value) > _MAX_IDENTITY:
            raise ValueError("reconciliation identity exceeds its finite bound")


@dataclass(frozen=True, slots=True)
class ReconciliationRequest:
    """Bind one decision to exact claim ownership and durable evidence."""

    identity: ReconciliationIdentity
    target: ClaimToken
    decision: ExternalEffectState
    evidence: tuple[ResultRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ReconciliationIdentity):
            raise TypeError("reconciliation identity has the wrong type")
        if not isinstance(self.target, ClaimToken):
            raise TypeError("reconciliation target has the wrong type")
        if not isinstance(self.decision, ExternalEffectState):
            raise TypeError("reconciliation decision has the wrong enum type")
        if self.target.kind is not ClaimKind.REPORT_SUBMIT:
            raise ValueError("only report submission effects can be reconciled")
        if self.decision not in _DECISIONS:
            raise ValueError("reconciliation decision is not an allowed effect state")
        if not isinstance(self.evidence, tuple):
            raise TypeError("reconciliation evidence must be a tuple")
        if any(not isinstance(ref, ResultRef) for ref in self.evidence):
            raise TypeError("reconciliation evidence must contain result references")
        if len(self.evidence) > _MAX_EVIDENCE:
            raise ValueError("reconciliation evidence exceeds its finite bound")
        if len(set(self.evidence)) != len(self.evidence):
            raise ValueError("reconciliation evidence references must be unique")
        if self.decision is not ExternalEffectState.UNKNOWN and not self.evidence:
            raise ValueError("definite reconciliation requires durable evidence")


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    """Describe one immutable saved reconciliation and proof lineage."""

    identity: ReconciliationIdentity
    target: ClaimToken
    decision: ExternalEffectState
    evidence: tuple[ResultRef, ...]
    resolved_at: datetime


@dataclass(frozen=True, slots=True)
class ClaimAttemptSnapshot:
    """Expose immutable claim-attempt history without ORM access."""

    token: ClaimToken
    started_at: datetime
    finished_at: datetime | None
    terminal_status: TerminalStatus | None
    external_effect: ExternalEffectState


@dataclass(frozen=True, slots=True)
class ClaimInspection:
    """Bound restart inspection of current ownership and retained history."""

    claim_key: str
    current_token: ClaimToken | None
    current_effect: ExternalEffectState | None
    expires_at: datetime | None
    attempts: tuple[ClaimAttemptSnapshot, ...]
    reconciliations: tuple[ReconciliationResult, ...]
    history_truncated: bool


def validate_history_limit(value: int) -> int:
    """Return a bounded positive history limit."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("history limit must be an integer")
    if value < 1 or value > _MAX_HISTORY:
        raise ValueError("history limit must be between 1 and 100")
    return value
