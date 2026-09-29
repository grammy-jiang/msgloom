"""Claim validation helpers shared by Phase 1 writer transactions."""

from __future__ import annotations

from datetime import datetime
from math import isfinite

from sqlalchemy import select
from sqlalchemy.engine import Connection, RowMapping

from msgloom.contracts import ClaimToken, ExternalEffectState, StageResult
from msgloom.persistence.errors import StaleClaimError
from msgloom.persistence.records import CLAIM_ATTEMPTS, RECONCILIATIONS, WORK_CLAIMS


def require_proven_effect_not_downgraded(
    current: ExternalEffectState, proposed: ExternalEffectState
) -> None:
    """Keep accepted provider proof from becoming retry-safe."""
    if current is ExternalEffectState.ACCEPTED and proposed in {
        ExternalEffectState.ACCEPTED,
        ExternalEffectState.CONFIRMED,
    }:
        return
    if (
        current is ExternalEffectState.CONFIRMED
        and proposed is ExternalEffectState.CONFIRMED
    ):
        return
    if current in {ExternalEffectState.ACCEPTED, ExternalEffectState.CONFIRMED}:
        raise StaleClaimError("proven external effect cannot be downgraded")


def validate_lease_seconds(value: float) -> float:
    """Return one finite non-negative lease value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("claim lease must be a finite non-negative number")
    lease = float(value)
    if not isfinite(lease) or lease < 0:
        raise ValueError("claim lease must be a finite non-negative number")
    return lease


def require_current_claim(
    connection: Connection,
    token: ClaimToken,
    *,
    now: datetime,
    require_unexpired: bool = True,
) -> RowMapping:
    """Require exact durable ownership, optionally including a live lease."""
    current = (
        connection.execute(
            select(WORK_CLAIMS).where(WORK_CLAIMS.c.claim_key == token.claim_key)
        )
        .mappings()
        .first()
    )
    if current is None:
        raise StaleClaimError("claim attempt no longer owns this scope")
    if (
        current["claim_token"] != token.token
        or current["claim_kind"] != token.kind.value
        or current["execution_id"] != token.execution.value
        or current["attempt_id"] != token.attempt.value
    ):
        raise StaleClaimError("claim token metadata does not match current owner")
    if require_unexpired and claim_is_expired(current, now):
        raise StaleClaimError("claim lease expired before durable publication")
    return current


def require_claim_publication(
    connection: Connection,
    token: ClaimToken,
    result: StageResult,
    *,
    now: datetime,
) -> None:
    """Fence a result publication to one live enclosing operation claim."""
    require_current_claim(connection, token, now=now)
    require_unreconciled_claim(connection, token)
    attempt = claim_attempt(connection, token)
    if attempt["finished_at"] is not None:
        raise StaleClaimError("terminal claim attempt cannot publish new results")
    if result.execution != token.execution:
        raise StaleClaimError("result execution does not match claim execution")


def require_unreconciled_claim(connection: Connection, token: ClaimToken) -> None:
    """Reject old-owner mutations after later recovery proof was committed."""
    reconciled = connection.execute(
        select(RECONCILIATIONS.c.reconciliation_id).where(
            RECONCILIATIONS.c.claim_token == token.token
        )
    ).first()
    if reconciled is not None:
        raise StaleClaimError("claim attempt was resolved by reconciliation")


def claim_attempt(connection: Connection, token: ClaimToken) -> RowMapping:
    """Load exact immutable claim-attempt history for a token."""
    attempt = (
        connection.execute(
            select(CLAIM_ATTEMPTS).where(CLAIM_ATTEMPTS.c.claim_token == token.token)
        )
        .mappings()
        .first()
    )
    if attempt is None:
        raise StaleClaimError("claim attempt history is missing")
    if (
        attempt["claim_key"] != token.claim_key
        or attempt["claim_kind"] != token.kind.value
        or attempt["execution_id"] != token.execution.value
        or attempt["attempt_id"] != token.attempt.value
    ):
        raise StaleClaimError("claim token metadata does not match attempt history")
    return attempt


def claim_is_expired(claim: RowMapping, now: datetime) -> bool:
    """Return whether the durable lease is no longer active."""
    return _parse_time(claim["expires_at"]) <= now


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("stored claim time must be timezone-aware")
    return parsed
