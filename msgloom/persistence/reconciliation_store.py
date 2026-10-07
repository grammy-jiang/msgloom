"""Atomic domain operations for external-effect reconciliation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.engine import Connection, RowMapping

from msgloom.contracts import (
    AttemptIdentity,
    ClaimKind,
    ClaimToken,
    ExecutionIdentity,
    ExternalEffectState,
    ResultRef,
    TerminalStatus,
)
from msgloom.persistence.claim_store import (
    claim_attempt,
    claim_is_expired,
    require_current_claim,
)
from msgloom.persistence.codecs import decode_result_refs, encode_result_refs
from msgloom.persistence.errors import ImmutableRecordError, StaleClaimError
from msgloom.persistence.reconciliation import (
    ClaimAttemptSnapshot,
    ClaimInspection,
    ReconciliationIdentity,
    ReconciliationRequest,
    ReconciliationResult,
    validate_history_limit,
    validate_reconciliation_request,
)
from msgloom.persistence.records import CLAIM_ATTEMPTS, RECONCILIATIONS, WORK_CLAIMS

_ALLOWED_FROM_UNCERTAIN = frozenset(
    {
        ExternalEffectState.UNKNOWN,
        ExternalEffectState.ACCEPTED,
        ExternalEffectState.CONFIRMED,
        ExternalEffectState.REJECTED,
    }
)


def reconcile_effect(
    connection: Connection,
    request: ReconciliationRequest,
    require_inputs: Callable[[Connection, tuple[ResultRef, ...]], None],
) -> ReconciliationResult:
    """Save proof and update retry gating in one caller-owned transaction."""
    request = validate_reconciliation_request(request)
    existing = _existing(connection, request.identity)
    if existing is not None:
        saved = _result_from_row(existing)
        if _same_request(saved, request):
            return saved
        raise ImmutableRecordError("reconciliation identity is immutable")

    require_inputs(connection, request.evidence)
    now = datetime.now(UTC)
    current = require_current_claim(
        connection, request.target, now=now, require_unexpired=False
    )
    attempt = claim_attempt(connection, request.target)
    if attempt["finished_at"] is None and not claim_is_expired(current, now):
        raise StaleClaimError("active claim owner cannot be reconciled")
    current_effect = ExternalEffectState(current["external_effect"])
    _require_transition(current_effect, request.decision)

    append_reconciliation(connection, request, now)
    if request.decision is ExternalEffectState.REJECTED:
        connection.execute(
            delete(WORK_CLAIMS).where(WORK_CLAIMS.c.claim_token == request.target.token)
        )
    else:
        connection.execute(
            update(WORK_CLAIMS)
            .where(WORK_CLAIMS.c.claim_token == request.target.token)
            .values(
                external_effect=request.decision.value,
                expires_at=_time(now),
            )
        )
    return ReconciliationResult(
        identity=request.identity,
        target=request.target,
        decision=request.decision,
        evidence=request.evidence,
        resolved_at=now,
    )


def append_reconciliation(
    connection: Connection,
    request: ReconciliationRequest,
    resolved_at: datetime,
) -> None:
    """Append one immutable reconciliation row inside the caller transaction."""
    connection.execute(RECONCILIATIONS.insert().values(**_values(request, resolved_at)))


def inspect_claim(
    connection: Connection, claim_key: str, history_limit: int
) -> ClaimInspection:
    """Read bounded current ownership, attempt history, and reconciliations."""
    if not isinstance(claim_key, str) or not claim_key.strip():
        raise ValueError("claim key must be non-empty")
    limit = validate_history_limit(history_limit)
    current = (
        connection.execute(
            select(WORK_CLAIMS).where(WORK_CLAIMS.c.claim_key == claim_key)
        )
        .mappings()
        .first()
    )
    attempt_rows = (
        connection.execute(
            select(CLAIM_ATTEMPTS)
            .where(CLAIM_ATTEMPTS.c.claim_key == claim_key)
            .order_by(CLAIM_ATTEMPTS.c.started_at.desc())
            .limit(limit + 1)
        )
        .mappings()
        .all()
    )
    reconciliation_rows = (
        connection.execute(
            select(RECONCILIATIONS)
            .where(RECONCILIATIONS.c.claim_key == claim_key)
            .order_by(RECONCILIATIONS.c.resolved_at.desc())
            .limit(limit + 1)
        )
        .mappings()
        .all()
    )
    truncated = len(attempt_rows) > limit or len(reconciliation_rows) > limit
    attempts = tuple(_attempt_from_row(row) for row in attempt_rows[:limit])
    reconciliations = tuple(
        _result_from_row(row) for row in reconciliation_rows[:limit]
    )
    return ClaimInspection(
        claim_key=claim_key,
        current_token=None if current is None else _token_from_row(current),
        current_effect=(
            None if current is None else ExternalEffectState(current["external_effect"])
        ),
        expires_at=None if current is None else _parse_time(current["expires_at"]),
        attempts=attempts,
        reconciliations=reconciliations,
        history_truncated=truncated,
    )


def _require_transition(
    current: ExternalEffectState, decision: ExternalEffectState
) -> None:
    if current in {ExternalEffectState.PENDING, ExternalEffectState.UNKNOWN}:
        if decision in _ALLOWED_FROM_UNCERTAIN:
            return
    elif (
        current is ExternalEffectState.ACCEPTED
        and decision is ExternalEffectState.CONFIRMED
    ):
        return
    raise StaleClaimError("external effect is not eligible for this reconciliation")


def _existing(
    connection: Connection, identity: ReconciliationIdentity
) -> RowMapping | None:
    return (
        connection.execute(
            select(RECONCILIATIONS).where(
                RECONCILIATIONS.c.reconciliation_id == identity.value
            )
        )
        .mappings()
        .first()
    )


def _same_request(saved: ReconciliationResult, request: ReconciliationRequest) -> bool:
    return (
        saved.identity == request.identity
        and saved.target == request.target
        and saved.decision is request.decision
        and saved.evidence == request.evidence
    )


def _values(request: ReconciliationRequest, resolved_at: datetime) -> dict[str, str]:
    token = request.target
    return {
        "reconciliation_id": request.identity.value,
        "claim_token": token.token,
        "claim_key": token.claim_key,
        "claim_kind": token.kind.value,
        "execution_id": token.execution.value,
        "attempt_id": token.attempt.value,
        "decision": request.decision.value,
        "evidence_refs": encode_result_refs(request.evidence),
        "resolved_at": _time(resolved_at),
    }


def _result_from_row(row: RowMapping) -> ReconciliationResult:
    return ReconciliationResult(
        identity=ReconciliationIdentity(row["reconciliation_id"]),
        target=_token_from_row(row),
        decision=ExternalEffectState(row["decision"]),
        evidence=decode_result_refs(row["evidence_refs"]),
        resolved_at=_parse_time(row["resolved_at"]),
    )


def _attempt_from_row(row: RowMapping) -> ClaimAttemptSnapshot:
    status = row["terminal_status"]
    return ClaimAttemptSnapshot(
        token=_token_from_row(row),
        started_at=_parse_time(row["started_at"]),
        finished_at=(
            None if row["finished_at"] is None else _parse_time(row["finished_at"])
        ),
        terminal_status=None if status is None else TerminalStatus(status),
        external_effect=ExternalEffectState(row["external_effect"]),
    )


def _token_from_row(row: RowMapping) -> ClaimToken:
    return ClaimToken(
        claim_key=row["claim_key"],
        token=row["claim_token"],
        kind=ClaimKind(row["claim_kind"]),
        execution=ExecutionIdentity(row["execution_id"]),
        attempt=AttemptIdentity(row["attempt_id"]),
    )


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("stored reconciliation time must be timezone-aware")
    return parsed


def _time(value: datetime) -> str:
    return value.isoformat(timespec="microseconds")
