"""Shared fixtures and helpers for the C0-14b finalizer tests (``tmp_path`` only)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.identity import AttemptProof, stage_metadata
from msgloom.a2_kedro.contracts.receipt import (
    CompletionReceipt,
    TerminalRoot,
    TransitionBatch,
)
from msgloom.contracts import (
    Limitation,
    ResultRef,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence.a2_acceptance_models import AcceptedStage
from msgloom.persistence.a2_receipt_errors import A2ReceiptError
from msgloom.persistence.a2_receipt_store import ReceiptStore
from msgloom.persistence.a2_schema import acquire_claim
from msgloom.persistence.a2_workset_finalize import (
    A2FinalizeError,
    FinalizeRequest,
    FinalizeResult,
    finalize_a2_intake_workset_v2,
)
from msgloom.persistence.codecs import encode_result_refs
from msgloom.persistence.records import result_values
from msgloom.preparation_pipeline.intake_models import (
    PreparationIntakeWorkset,
    workset_claim_key,
)
from tests.a2_kedro.helpers import (
    WORKSET_REF,
    accepted_ref,
    check,
    hexd,
    result_for,
    stage_identity,
    workset,
)
from tests.persistence.test_a2_schema_fixtures import build_schema5, raw

CANARY = "CANARY-PII-9d2e-carol@example.invalid"
COMPLETE = TerminalStatus.COMPLETE
BATCH_REF = accepted_ref("5", "prepared_transitions", "2")
ROW = (
    "SELECT state, terminal_status, result_refs, terminal_claim_token, "
    "terminal_execution_id, terminal_attempt_id "
    "FROM phase1_preparation_intake_worksets"
)
PENDING = ("pending", None, "[]", None, None, None)


class InjectedStop(BaseException):
    """A BaseException that is not an Exception, like KeyboardInterrupt."""


class Hooked:
    """Forwarding connection wrapper: records SQL, fails a statement prefix."""

    def __init__(
        self,
        inner: sqlite3.Connection,
        fail: tuple[str, BaseException] | None = None,
    ) -> None:
        self.inner = inner
        self.fail = fail
        self.seen: list[str] = []

    @property
    def in_transaction(self) -> bool:
        return self.inner.in_transaction

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        self.seen.append(sql)
        if self.fail is not None and sql.startswith(self.fail[0]):
            error, self.fail = self.fail[1], None
            raise error
        return self.inner.execute(sql, *args)  # type: ignore[arg-type]


def attempt_proof(attempt: str = "a1", token: str = "c") -> AttemptProof:
    return AttemptProof(
        execution_id="exec-" + attempt,
        attempt_id=attempt,
        claim_key=workset_claim_key(WORKSET_REF.result_id),
        claim_token_sha256=hexd(token),
    )


def saved_result(
    ref: ResultRef,
    char: str,
    writer: AttemptProof,
    status: TerminalStatus = COMPLETE,
    limitations: tuple[Limitation, ...] = (),
) -> StageResult:
    """Return the saved ``StageResult`` a publisher ``writer`` stored for ``ref``."""
    return result_for(
        stage_identity(),
        result_id=ref.result_id,
        kind=ref.kind,
        schema_version=ref.schema_version,
        attempt=writer.attempt_id,
        status=status,
        limitations=limitations,
        sha=hexd(char),
    )


def stage_for(
    ref: ResultRef,
    char: str,
    writer: AttemptProof,
    status: TerminalStatus = COMPLETE,
    limitations: tuple[Limitation, ...] = (),
) -> AcceptedStage:
    """Return the accepted record that derives from :func:`saved_result`."""
    meta = stage_metadata(saved_result(ref, char, writer, status, limitations))
    return AcceptedStage(
        logical_key=ref.result_id,
        output=ref,
        canonical_sha256=meta.semantic_sha256,
        canonical_byte_count=meta.semantic_byte_count,
        semantic_data_id=meta.semantic_data_id,
        stage_metadata_sha256=meta.digest(),
        lineage_digest=meta.lineage_digest,
        status=meta.status,
        limitations_digest=meta.limitations_digest,
        writer=writer,
    )


@dataclass
class Env:
    path: Path
    db: sqlite3.Connection
    store: ReceiptStore
    ws: PreparationIntakeWorkset
    receipt: CompletionReceipt
    accepted: dict[str, AcceptedStage]
    claim_seq: int

    def request(
        self,
        receipt: CompletionReceipt | None = None,
        proof: AttemptProof | None = None,
        ws: PreparationIntakeWorkset | None = None,
    ) -> FinalizeRequest:
        return FinalizeRequest(
            ws or self.ws,
            WORKSET_REF,
            receipt or self.receipt,
            proof or attempt_proof(),
        )

    def rows(self) -> list[tuple[Any, ...]]:
        return [tuple(r) for r in self.db.execute(ROW)]

    def files(self) -> list[str]:
        return sorted(p.name for p in self.store._root.rglob("*") if p.is_file())

    def snapshot(self) -> tuple[Any, ...]:
        names = (
            "a2_claims",
            "a2_accepted_stages",
            "a2_stage_attempts",
            "stage_results",
        )
        extra = [list(self.db.execute(f"SELECT * FROM phase1_{n}")) for n in names]
        return (self.rows(), extra, self.files())

    def run(self) -> FinalizeResult:
        return finalize_a2_intake_workset_v2(self.db, self.store, self.request())


def make_receipt(
    ws: PreparationIntakeWorkset, policy: str = "policy-1", transitions: bool = True
) -> CompletionReceipt:
    refs = [accepted_ref(str(i + 1), "prepared", "2") for i in range(2)]
    roots = tuple(
        TerminalRoot(
            workset_selection_index=i,
            result=ref,
            disposition="prepared",
            status=COMPLETE,
            selection=ws.selections[i],
        )
        for i, ref in enumerate(refs)
    )
    batch = TransitionBatch(
        transitions=ws.transitions, result=BATCH_REF, status=COMPLETE
    )
    return CompletionReceipt(
        workset=WORKSET_REF,
        status=COMPLETE,
        policy_version=policy,
        roots=roots,
        transition_batch=batch if transitions else None,
    )


def workset_result() -> StageResult:
    ref = WORKSET_REF
    return result_for(
        stage_identity(), result_id=ref.result_id, kind=ref.kind, schema_version="1"
    )


def insert_row(db: sqlite3.Connection, table: str, values: dict[str, Any]) -> None:
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    db.execute(
        f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(values.values())
    )


def publish(
    db: sqlite3.Connection,
    stage: AcceptedStage,
    seq: int,
    result: StageResult | None = None,
    attempts: bool = True,
) -> None:
    """Store a saved result, its accepted record and its history row."""
    if result is not None:
        insert_row(db, "phase1_stage_results", result_values(result))
    insert_row(db, "phase1_a2_accepted_stages", accepted_columns(stage, seq))
    if attempts:
        insert_row(
            db,
            "phase1_a2_stage_attempts",
            {"logical_key": stage.logical_key, "claim_seq": seq, "outcome": "inserted"},
        )


def build_env(tmp_path: Path) -> Iterator[Env]:
    path = build_schema5(tmp_path / "a2.sqlite")
    (tmp_path / "proofs").mkdir()
    db = raw(path)
    ws = workset(selected=2, transitions=2)
    insert_row(db, "phase1_stage_results", result_values(workset_result()))
    cutoff = ws.cutoff
    insert_row(
        db,
        "phase1_preparation_intake_worksets",
        {
            "result_id": WORKSET_REF.result_id,
            "scope_key": ws.scope.claim_key(),
            "cutoff_release_entry_seq": cutoff.last_release_entry_seq,
            "cutoff_release_entry_digest": cutoff.last_release_entry_digest or "",
            "state": "pending",
            "result_refs": encode_result_refs(()),
        },
    )
    seq = acquire_claim(db, attempt_proof())
    if seq is None:
        pytest.fail("fixture claim must be acquired")
    receipt = make_receipt(ws)
    accepted: dict[str, AcceptedStage] = {}
    for char, ref in zip(
        "abe", [r.result for r in receipt.roots] + [BATCH_REF], strict=True
    ):
        writer = attempt_proof()
        stage = stage_for(ref, char, writer)
        accepted[ref.result_id] = stage
        publish(db, stage, seq, saved_result(ref, char, writer))
    yield Env(path, db, ReceiptStore(tmp_path / "proofs"), ws, receipt, accepted, seq)
    db.close()


def accepted_columns(stage: AcceptedStage, seq: int) -> dict[str, Any]:
    return {
        "logical_key": stage.logical_key,
        "kind": stage.output.kind,
        "schema_version": stage.output.schema_version,
        "status": stage.status.value,
        "canonical_sha256": stage.canonical_sha256,
        "canonical_byte_count": stage.canonical_byte_count,
        "semantic_data_id": stage.semantic_data_id,
        "stage_metadata_sha256": stage.stage_metadata_sha256,
        "lineage_digest": stage.lineage_digest,
        "limitations_digest": stage.limitations_digest,
        "writer_claim_seq": seq,
        "record_sha256": stage.record_sha256(),
        "record_json": stage.record_bytes().decode(),
    }


def refuse(
    env: Env,
    reason: str,
    request: FinalizeRequest | None = None,
    error: type[A2ReceiptError] = A2FinalizeError,
) -> A2ReceiptError:
    before = env.snapshot()
    with pytest.raises(error) as caught:
        finalize_a2_intake_workset_v2(env.db, env.store, request or env.request())
    check(
        caught.value.reason == reason, f"expected {reason}, got {caught.value.reason}"
    )
    check(str(caught.value) == reason, "message must be the reason code only")
    check(caught.value.__cause__ is None, "raw error must not chain")
    check(not env.db.in_transaction, "transaction must be closed")
    check(env.snapshot() == before, "a refused finalize must change nothing")
    return caught.value
