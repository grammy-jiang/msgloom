"""
Producer binding and the bidirectional v1/v2 Workset writer fence.

CANDIDATE/RESEARCH (C0-14c). Nothing here runs against a real database.
Tests use disposable files under ``tmp_path``.

One Workset must be finalized by exactly one producer: the legacy (v1)
finalizer in ``intake_store`` or the Kedro (v2) finalizer in
``a2_workset_finalize``. This module owns the fence and the binding. It adds
no table, no column and no schema revision. Every marker is derived from rows
that already exist.

Derived producer marker
-----------------------

A terminal ``phase1_preparation_intake_worksets`` row stores the claim token
of its finalizer. The two finalizers store different values:

* v1 stores the raw token. The same token is the primary key of one
  ``phase1_claim_attempts`` row (same claim key, execution and attempt).
* v2 stores the SHA-256 of the token. The same digest, claim key, execution
  and attempt form one ``phase1_a2_claims`` row (schema 5 only).

:func:`workset_owner` returns ``"v2"`` or ``"legacy"`` when exactly one of
the two proofs matches the terminal row. It fails closed with
:exc:`A2ProducerFenceError` when both match (``producer-ambiguous``) or when
neither matches (``terminal-owner-unproven``, for example a forged row).

The fence
---------

* v1 side: :func:`require_v1_writer_allowed` is called by the v1 finalizer
  in its terminal-history check. The call runs first, so the in-lock calls
  refuse before any write. It runs again before the generic immutable
  refusal, so a v2 commit between two unlocked reads still gets the typed
  error. It raises when a v2 proof matches the terminal row. It does nothing,
  and reads only ``sqlite_master``, when the file has no
  ``phase1_a2_claims`` table. The error is also an
  :exc:`ImmutableRecordError`, so v1 callers keep one type.
* v2 side: :func:`finalize_a2_workset_fenced` wraps the C0-14b finalizer.
  Before the lock it refuses a Workset that v1 finalized or whose terminal
  owner is unproven, and it requires v2 proof for every accepted stage in
  the receipt. This check only reads, so a failure cannot leave a partial
  write. The authority is still the finalizer lock: a v1 row that appears
  after the check makes the finalizer raise ``A2FinalizeConflict`` (v1 and
  v2 terminal values always differ). The wrapper re-reads the owner and maps
  that conflict to ``legacy-finalized``.

Whichever finalizer commits first wins. The loser raises
:exc:`A2ProducerFenceError` and writes nothing.

Mixed attempts
--------------

A Workset may have attempts of both producers. Stage history from legacy
attempts stays valid for v1 and is not rewritten. :func:`bind_workset_producers`
lists each attempt of the Workset PREPARE claim key with its
producer. :func:`stage_producer` decides who wrote one stage, and
:func:`require_v2_proven` refuses a stage whose writer attempt is legacy
(``legacy-attempt-stage``) or unknown (``stage-unproven``). A legacy stage is
never counted as v2-proven. An ``(execution, attempt)`` pair present in both
producers is ambiguous and refused. Producers must use distinct identities.

Open items
----------

* The v1 store refuses to open a schema 5 file. The v1 hook therefore guards
  a store opened before migration (a long-lived process), not a fresh open.
* The bare C0-14b function is not fenced by itself. This task may not edit
  that file. Production callers must use the wrapper. Race safety does not
  depend on the wrapper, because the finalizer lock refuses a v1 terminal
  row, but the typed reason does.
* No SQL marker is stored at claim time, so v1 is not blocked while v2 only
  holds a live claim. Blocking at claim time needs a schema revision.

Privacy: errors carry fixed reason codes only, never an id, token or digest.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from msgloom.persistence.a2_receipt_errors import A2ReceiptError
from msgloom.persistence.errors import ImmutableRecordError
from msgloom.preparation_pipeline.intake_models import workset_claim_key

if TYPE_CHECKING:
    from msgloom.persistence.a2_receipt_store import ReceiptStore
    from msgloom.persistence.a2_workset_finalize import (
        FinalizeRequest,
        FinalizeResult,
    )

Producer = Literal["legacy", "v2"]

_ROW = (
    "SELECT state, terminal_claim_token, terminal_execution_id, "
    "terminal_attempt_id FROM phase1_preparation_intake_worksets "
    "WHERE result_id = ?"
)
_A2_TABLE = (
    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'phase1_a2_claims'"
)
_V2_TERMINAL = (
    "SELECT 1 FROM phase1_a2_claims WHERE claim_key = ? AND execution_id = ? "
    "AND attempt_id = ? AND claim_token_sha256 = ?"
)
_V1_TERMINAL = (
    "SELECT 1 FROM phase1_claim_attempts WHERE claim_key = ? "
    "AND execution_id = ? AND attempt_id = ? AND claim_token = ?"
)
_V2_ATTEMPT = "SELECT 1 FROM phase1_a2_claims WHERE execution_id = ? AND attempt_id = ?"
_V1_ATTEMPT = (
    "SELECT 1 FROM phase1_claim_attempts WHERE execution_id = ? AND attempt_id = ?"
)
_V2_KEY_ATTEMPTS = (
    "SELECT execution_id, attempt_id FROM phase1_a2_claims "
    "WHERE claim_key = ? ORDER BY claim_seq"
)
_V1_KEY_ATTEMPTS = (
    "SELECT execution_id, attempt_id FROM phase1_claim_attempts "
    "WHERE claim_key = ? ORDER BY started_at, claim_token"
)
_STAGE_WRITER = (
    "SELECT c.execution_id, c.attempt_id FROM phase1_a2_accepted_stages s "
    "JOIN phase1_a2_claims c ON c.claim_seq = s.writer_claim_seq "
    "WHERE s.logical_key = ?"
)
_SAVED_WRITER = (
    "SELECT execution_id, attempt_id FROM phase1_stage_results WHERE result_id = ?"
)


class A2ProducerFenceError(A2ReceiptError, ImmutableRecordError):
    """A writer was refused by the fence. ``reason`` is a fixed code."""


@dataclass(frozen=True, slots=True, repr=False)
class AttemptBinding:
    """One attempt and the producer that owned it."""

    execution_id: str
    attempt_id: str
    producer: Producer

    def __repr__(self) -> str:
        return f"AttemptBinding({self.producer})"


@dataclass(frozen=True, slots=True, repr=False)
class ProducerBinding:
    """The terminal owner (or ``None``) and every Workset-key attempt."""

    owner: Producer | None
    attempts: tuple[AttemptBinding, ...]

    def __repr__(self) -> str:
        return f"ProducerBinding({self.owner})"


def _all(db: Any, sql: str, params: Sequence[object] = ()) -> list[tuple[Any, ...]]:
    """Run one read on a ``sqlite3`` or SQLAlchemy connection."""
    run: Any = getattr(db, "exec_driver_sql", None)
    cursor = run(sql, tuple(params)) if run is not None else db.execute(sql, params)
    return [tuple(row) for row in cursor.fetchall()]


def _has_a2_tables(db: Any) -> bool:
    return bool(_all(db, _A2_TABLE))


def _terminal_proofs(db: Any, result_id: str) -> tuple[bool, bool, bool]:
    """Return ``(terminal, v2_match, v1_match)`` for the Workset row."""
    rows = _all(db, _ROW, (result_id,))
    if not rows or rows[0][0] != "terminal":
        return False, False, False
    token, execution, attempt = rows[0][1:]
    if not isinstance(token, str) or execution is None or attempt is None:
        return True, False, False
    key = workset_claim_key(result_id)
    v2 = _has_a2_tables(db) and bool(
        _all(db, _V2_TERMINAL, (key, execution, attempt, token))
    )
    v1 = bool(_all(db, _V1_TERMINAL, (key, execution, attempt, token)))
    return True, v2, v1


def workset_owner(db: Any, result_id: str) -> Producer | None:
    """
    Return the producer that finalized the Workset, or ``None`` if pending.

    Raises :exc:`A2ProducerFenceError` (``producer-ambiguous`` or
    ``terminal-owner-unproven``) when the terminal row has no unique proof.
    """
    terminal, v2, v1 = _terminal_proofs(db, result_id)
    if not terminal:
        return None
    if v1 and v2:
        raise A2ProducerFenceError("producer-ambiguous")
    if v2:
        return "v2"
    if v1:
        return "legacy"
    raise A2ProducerFenceError("terminal-owner-unproven")


def require_v1_writer_allowed(db: Any, result_id: str) -> None:
    """
    Refuse the v1 finalizer when v2 finalized the Workset (the v1 hook).

    Read only. Call it inside the v1 write transaction. With no A2 table the
    cost is one ``sqlite_master`` read and the v1 behavior is unchanged.
    """
    if not _has_a2_tables(db):
        return
    _, v2, _ = _terminal_proofs(db, result_id)
    if v2:
        raise A2ProducerFenceError("v2-finalized")


def attempt_producer(db: Any, execution_id: str, attempt_id: str) -> Producer | None:
    """Return the producer of an attempt, ``None`` if unknown, or refuse."""
    pair = (execution_id, attempt_id)
    v2 = _has_a2_tables(db) and bool(_all(db, _V2_ATTEMPT, pair))
    v1 = bool(_all(db, _V1_ATTEMPT, pair))
    if v1 and v2:
        raise A2ProducerFenceError("attempt-ambiguous")
    return "v2" if v2 else "legacy" if v1 else None


def bind_workset_producers(db: Any, result_id: str) -> ProducerBinding:
    """Record the owner and the producer of each Workset PREPARE attempt."""
    key = workset_claim_key(result_id)
    attempts: list[AttemptBinding] = []
    if _has_a2_tables(db):
        attempts += [
            AttemptBinding(e, a, "v2") for e, a in _all(db, _V2_KEY_ATTEMPTS, (key,))
        ]
    attempts += [
        AttemptBinding(e, a, "legacy") for e, a in _all(db, _V1_KEY_ATTEMPTS, (key,))
    ]
    for item in attempts:
        attempt_producer(db, item.execution_id, item.attempt_id)
    return ProducerBinding(workset_owner(db, result_id), tuple(attempts))


def stage_producer(db: Any, logical_key: str) -> Producer | None:
    """Return who wrote a stage: ``v2`` only with an accepted v2 record."""
    if rows := _all(db, _STAGE_WRITER, (logical_key,)):
        if attempt_producer(db, *rows[0]) != "v2":
            raise A2ProducerFenceError("stage-writer-forged")
        return "v2"
    if rows := _all(db, _SAVED_WRITER, (logical_key,)):
        return "legacy" if attempt_producer(db, *rows[0]) == "legacy" else None
    return None


def require_v2_proven(db: Any, logical_keys: Sequence[str]) -> None:
    """Refuse any stage that no v2 accepted record and attempt proves."""
    for key in logical_keys:
        match stage_producer(db, key):
            case "v2":
                continue
            case "legacy":
                raise A2ProducerFenceError("legacy-attempt-stage")
            case _:
                raise A2ProducerFenceError("stage-unproven")


def _fenced[T](action: Callable[[], T]) -> T:
    """Map a database failure of a fence read to a fixed reason code."""
    try:
        return action()
    except sqlite3.Error:
        raise A2ProducerFenceError("fence-check-failed") from None


def _receipt_keys(request: FinalizeRequest) -> list[str]:
    receipt = request.receipt
    refs = [root.result for root in receipt.roots]
    if receipt.transition_batch is not None:
        refs.append(receipt.transition_batch.result)
    return [ref.result_id for ref in refs]


def _precheck(db: sqlite3.Connection, request: FinalizeRequest) -> None:
    """Read only. Refuse a legacy-owned Workset and unproven v2 stages."""
    if not _has_a2_tables(db):
        return
    if workset_owner(db, request.workset_ref.result_id) == "legacy":
        raise A2ProducerFenceError("legacy-finalized")
    require_v2_proven(db, _receipt_keys(request))


def finalize_a2_workset_fenced(
    db: sqlite3.Connection, store: ReceiptStore, request: FinalizeRequest
) -> FinalizeResult:
    """
    Run the C0-14b v2 finalizer behind the producer fence.

    Raises :exc:`A2ProducerFenceError` when v1 finalized the Workset, when
    the owner is unproven or when a receipt stage is not v2-proven. Every
    other result and error is the finalizer's own. No fence path writes.
    """
    from msgloom.persistence.a2_workset_finalize import (
        A2FinalizeConflict,
        finalize_a2_intake_workset_v2,
    )

    _fenced(lambda: _precheck(db, request))
    try:
        return finalize_a2_intake_workset_v2(db, store, request)
    except A2FinalizeConflict:
        owner = _fenced(lambda: workset_owner(db, request.workset_ref.result_id))
        if owner == "legacy":
            raise A2ProducerFenceError("legacy-finalized") from None
        raise
