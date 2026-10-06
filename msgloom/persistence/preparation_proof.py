"""Exact producer bindings and receipts within the caller's transaction."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.engine import Connection, RowMapping

from msgloom.contracts import (
    ClaimKind,
    ClaimToken,
    ExternalEffectState,
    ResultRef,
    ResultSchemaRegistry,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence.claim_store import (
    claim_attempt,
    require_claim_publication,
    require_current_claim,
    require_unreconciled_claim,
)
from msgloom.persistence.codecs import decode_result_refs, encode_result_refs
from msgloom.persistence.errors import (
    DependencyNotReadyError,
    ImmutableRecordError,
    StaleClaimError,
)
from msgloom.persistence.intake_records import saved_result
from msgloom.persistence.records import (
    CLAIM_ATTEMPTS,
    RECONCILIATIONS,
    STAGE_RESULTS,
    WORK_CLAIMS,
)
from msgloom.persistence.records import (
    PREPARATION_PLAN_PROOFS as PLANS,
)
from msgloom.persistence.records import (
    PREPARATION_RESULT_BINDINGS as BINDINGS,
)

_ACCEPTED = {TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE}
_KINDS = {
    "collected_selection",
    "derived_bytes",
    "prepared",
    "filter_result",
    "group_result",
}
_IDENTITY = ("claim_token", "claim_key", "claim_kind", "execution_id", "attempt_id")
_HEADER = (*_IDENTITY, "required_inputs", "configuration_version", "code_version")


@dataclass(frozen=True)
class AcceptedPreparationProof:
    """Keep receipt, attribution, and history snapshots for writer recheck."""

    plan: RowMapping
    attempt: RowMapping
    bindings: tuple[RowMapping, ...]
    results: tuple[StageResult, ...]


def _references(refs: tuple[ResultRef, ...]) -> str:
    """
    Encode closed, unique references with a four-MiB metadata ceiling.

    Manual manifests may exceed intake's 1024-output ceiling; no proof is
    truncated. Intake independently rejects a manifest exceeding its bound.
    """
    if (
        type(refs) is not tuple
        or any(
            not isinstance(ref, ResultRef)
            or ref.kind not in _KINDS
            or ref.schema_version != "1"
            or not ref.result_id.strip()
            or len(ref.result_id.encode()) > 2048
            for ref in refs
        )
        or len(set(refs)) != len(refs)
    ):
        raise DependencyNotReadyError("preparation proof needs closed exact references")
    encoded = encode_result_refs(refs)
    if len(encoded.encode()) > 4 * 1024 * 1024:
        raise DependencyNotReadyError("preparation proof exceeds metadata bound")
    return encoded


def _plan(connection: Connection, token: str) -> RowMapping | None:
    return (
        connection.execute(select(PLANS).where(PLANS.c.claim_token == token))
        .mappings()
        .first()
    )


def bind_preparation_result(
    connection: Connection,
    result: StageResult,
    token: ClaimToken | None,
) -> None:
    """
    Bind only new finite-plan publications, before result/data insertion.

    All rows share the caller's transaction and both publication fences. An
    immutable existing result without attribution can never acquire it later.
    Non-plan and metadata-only publications retain their legacy behavior.
    """
    if token is None or token.kind is not ClaimKind.PREPARE:
        return
    if not token.claim_key.startswith("prepare:"):
        return
    require_claim_publication(connection, token, result, now=datetime.now(UTC))
    if result.attempt != token.attempt:
        raise StaleClaimError("preparation result attempt differs from publishing plan")
    current = require_current_claim(connection, token, now=datetime.now(UTC))
    inputs = decode_result_refs(current["required_inputs"])
    _references(inputs)
    if any(ref.kind != "collected_selection" for ref in inputs):
        raise DependencyNotReadyError(
            "preparation plan inputs must be exact selections"
        )
    values = {key: current[key] for key in _IDENTITY}
    values.update(
        required_inputs=encode_result_refs(inputs),
        configuration_version=result.configuration_version,
        code_version=result.code_version,
    )
    if any(
        not value.strip() or len(value.encode()) > 2048
        for key, value in values.items()
        if key != "required_inputs"
    ):
        raise DependencyNotReadyError("preparation identity exceeds metadata bound")
    ref = ResultRef(result.result_id, result.kind, result.schema_version)
    _references((ref,))
    binding = (
        connection.execute(
            select(BINDINGS).where(BINDINGS.c.result_id == result.result_id)
        )
        .mappings()
        .first()
    )
    expected = {
        "result_id": ref.result_id,
        "kind": ref.kind,
        "schema_version": ref.schema_version,
        "claim_token": token.token,
    }
    if binding is not None and dict(binding) != expected:
        raise ImmutableRecordError("preparation result cannot be rebound")
    if (
        binding is None
        and connection.execute(
            select(STAGE_RESULTS.c.result_id).where(
                STAGE_RESULTS.c.result_id == ref.result_id
            )
        ).first()
        is not None
    ):
        raise ImmutableRecordError("historical unbound result cannot be adopted")
    plan = _plan(connection, token.token)
    if plan is None:
        if binding is not None:
            raise ImmutableRecordError("preparation binding lost its plan snapshot")
        connection.execute(PLANS.insert().values(**values))
    elif any(plan[key] != values[key] for key in _HEADER) or plan["accepted_status"]:
        raise ImmutableRecordError("preparation plan snapshot is immutable")
    if binding is None:
        connection.execute(BINDINGS.insert().values(**expected))


def _manifest(
    connection: Connection,
    plan: RowMapping,
    refs: tuple[ResultRef, ...],
    registry: ResultSchemaRegistry,
) -> tuple[tuple[RowMapping, ...], tuple[StageResult, ...]]:
    """Require every and only exact bound publication, using metadata only."""
    _references(refs)
    bindings = tuple(
        connection.execute(
            select(BINDINGS)
            .where(BINDINGS.c.claim_token == plan["claim_token"])
            .order_by(BINDINGS.c.result_id)
            .limit(len(refs) + 1)
        ).mappings()
    )
    if {
        ResultRef(row["result_id"], row["kind"], row["schema_version"])
        for row in bindings
    } != set(refs) or len(bindings) != len(refs):
        raise DependencyNotReadyError(
            "accepted manifest differs from exact publications"
        )
    results = tuple(saved_result(connection, ref, registry) for ref in refs)
    for result in results:
        if (
            result.execution.value != plan["execution_id"]
            or result.attempt.value != plan["attempt_id"]
            or result.configuration_version != plan["configuration_version"]
            or result.code_version != plan["code_version"]
            or result.status not in _ACCEPTED
        ):
            raise DependencyNotReadyError("publication differs from its exact plan")
    return bindings, results


def _accepted_history(connection: Connection, plan: RowMapping) -> RowMapping:
    """Reject missing, contradictory, unfinished, or still-owned history."""
    attempt = (
        connection.execute(
            select(CLAIM_ATTEMPTS).where(
                CLAIM_ATTEMPTS.c.claim_token == plan["claim_token"]
            )
        )
        .mappings()
        .first()
    )
    if (
        plan["claim_kind"] != ClaimKind.PREPARE.value
        or not plan["claim_key"].startswith("prepare:")
        or plan["accepted_status"] not in {item.value for item in _ACCEPTED}
        or attempt is None
        or any(attempt[key] != plan[key] for key in _IDENTITY)
        or attempt["finished_at"] is None
        or attempt["terminal_status"] != plan["accepted_status"]
        or attempt["external_effect"] != ExternalEffectState.NONE.value
        or connection.execute(
            select(RECONCILIATIONS.c.reconciliation_id).where(
                RECONCILIATIONS.c.claim_token == plan["claim_token"]
            )
        ).first()
        is not None
        or connection.execute(
            select(WORK_CLAIMS.c.claim_token).where(
                WORK_CLAIMS.c.claim_token == plan["claim_token"]
            )
        ).first()
        is not None
    ):
        raise DependencyNotReadyError("receipt lacks its exact accepted plan history")
    return attempt


def load_accepted_preparation(
    connection: Connection,
    token: str,
    registry: ResultSchemaRegistry,
) -> AcceptedPreparationProof:
    """Read an exact accepted receipt with bounded metadata and no payloads."""
    plan = _plan(connection, token)
    if plan is None or plan["accepted_result_refs"] is None:
        raise DependencyNotReadyError(
            "output lacks its exact accepted preparation receipt"
        )
    payload = plan["accepted_result_refs"]
    if len(payload.encode()) > 4 * 1024 * 1024:
        raise DependencyNotReadyError("preparation receipt exceeds metadata bound")
    refs = decode_result_refs(payload)
    bindings, results = _manifest(connection, plan, refs, registry)
    attempt = _accepted_history(connection, plan)
    return AcceptedPreparationProof(plan, attempt, bindings, results)


def accept_preparation_results(
    connection: Connection,
    token: ClaimToken,
    status: TerminalStatus,
    effect: ExternalEffectState,
    refs: tuple[ResultRef, ...],
    registry: ResultSchemaRegistry,
) -> None:
    """
    Atomically accept a producer's normal completion and release its claim.

    Only an explicit full manifest can create acceptance. Cleanup and lease
    supersession never call this path. Exact accepted retries are read-only;
    neither a replacement owner nor a different outcome can change the receipt.
    """
    if (
        token.kind is not ClaimKind.PREPARE
        or not token.claim_key.startswith("prepare:")
        or status not in _ACCEPTED
        or effect is not ExternalEffectState.NONE
    ):
        raise ValueError("only normal finite preparation completion can be accepted")
    encoded = _references(refs)
    plan = _plan(connection, token.token)
    require_unreconciled_claim(connection, token)
    attempt = claim_attempt(connection, token)
    if plan is not None and plan["accepted_status"] is not None:
        proof = load_accepted_preparation(connection, token.token, registry)
        if (
            proof.plan["accepted_status"] != status.value
            or proof.plan["accepted_result_refs"] != encoded
        ):
            raise ImmutableRecordError("accepted preparation receipt is immutable")
        return
    current = require_current_claim(connection, token, now=datetime.now(UTC))
    if attempt["finished_at"] is not None:
        raise StaleClaimError("finished attempt cannot gain preparation acceptance")
    if plan is None or any(
        plan[key] != current[key] for key in (*_IDENTITY, "required_inputs")
    ):
        raise DependencyNotReadyError(
            "acceptance lacks exact frozen publication identity"
        )
    if current["external_effect"] not in {
        ExternalEffectState.NONE.value,
        ExternalEffectState.NOT_STARTED.value,
    }:
        raise StaleClaimError("preparation claim has an incompatible external effect")
    publications = _manifest(connection, plan, refs, registry)
    connection.execute(
        update(PLANS)
        .where(PLANS.c.claim_token == token.token)
        .values(
            accepted_status=status.value,
            accepted_result_refs=encoded,
        )
    )
    connection.execute(
        update(CLAIM_ATTEMPTS)
        .where(CLAIM_ATTEMPTS.c.claim_token == token.token)
        .values(
            terminal_status=status.value,
            external_effect=effect.value,
            finished_at=datetime.now(UTC).isoformat(),
        )
    )
    # Fence after receipt/history writes while the exact live claim
    # still exists.
    fenced = require_current_claim(connection, token, now=datetime.now(UTC))
    require_unreconciled_claim(connection, token)
    accepted = _plan(connection, token.token)
    if (
        any(fenced[key] != current[key] for key in (*_IDENTITY, "required_inputs"))
        or accepted is None
        or any(accepted[key] != plan[key] for key in _HEADER)
        or accepted["accepted_status"] != status.value
        or accepted["accepted_result_refs"] != encoded
        or _manifest(connection, accepted, refs, registry) != publications
    ):
        raise ImmutableRecordError("preparation acceptance changed before commit")
    connection.execute(
        delete(WORK_CLAIMS).where(WORK_CLAIMS.c.claim_token == token.token)
    )
    load_accepted_preparation(connection, token.token, registry)
