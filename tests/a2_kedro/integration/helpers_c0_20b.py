"""
C0-20b helpers: a real A1 Workset, v2 accepted-stage rows and an A3 read.

Everything lives in one ``tmp_path`` SQLite file. The Workset, its stored
selections and its PREPARE claim come from the real Phase 1 helpers. The
accepted-stage rows reuse the C0-14b publishing helpers. Only the saved
``prepared@2`` payloads are new: their semantic reference matches real
canonical bytes, so the A3 v2 loader can verify them.
"""

from __future__ import annotations

import asyncio
import sqlite3
import traceback
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, select

from msgloom.a2_kedro.contracts.identity import AttemptProof, stage_metadata
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt, TerminalRoot
from msgloom.a2_kedro.contracts.results import Prepared
from msgloom.contracts import (
    Limitation,
    ResultRef,
    SemanticDataRef,
    StageResult,
    TerminalStatus,
)
from msgloom.persistence.a2_acceptance_models import AcceptedStage
from msgloom.persistence.a2_producer_binding import (
    finalize_a2_workset_fenced,
    workset_owner,
)
from msgloom.persistence.a2_receipt_store import ReceiptStore
from msgloom.persistence.a2_schema import acquire_claim, migrate_schema4_to_v5
from msgloom.persistence.a2_workset_finalize import FinalizeRequest, FinalizeResult
from msgloom.persistence.records import STAGE_RESULTS, result_from_row
from msgloom.persistence.store import Phase1Store
from msgloom.preparation_pipeline.intake_models import (
    PreparationIntakeWorkset,
    workset_claim_key,
)
from msgloom.triage_input.adapter_v2 import V2Hold, admit_upstream
from msgloom.triage_input.io_v2 import load_values
from tests.a2_kedro.helpers import accepted_ref, check, hexd, result_for, stage_identity
from tests.a2_kedro.helpers_c0_14b import ROW, insert_row, publish
from tests.a2_kedro.result_fixtures import make, prepared_data
from tests.persistence.test_a2_schema_fixtures import GATE, raw
from tests.phase1_foundation import intake_completion_helpers as c
from tests.phase1_foundation import intake_helpers as h

CANARY = "CANARY-PII-9d2e-carol@example.invalid"
COMPLETE = TerminalStatus.COMPLETE
INCOMPLETE = TerminalStatus.INCOMPLETE
HELD_KIND = "a2_input_disposition"
TABLES = ("a2_claims", "a2_accepted_stages", "a2_stage_attempts", "stage_results")


def limit_data(detail: str = CANARY) -> dict[str, str]:
    return {"code": "time_unknown", "detail": detail}


@dataclass
class World:
    """One migrated file with a real Workset, stage rows and a receipt."""

    path: Path
    store: Phase1Store
    value: PreparationIntakeWorkset
    ref: ResultRef
    proof: AttemptProof
    receipts: ReceiptStore
    receipt: CompletionReceipt
    prepared: list[ResultRef] = field(default_factory=list)

    def request(self, receipt: CompletionReceipt | None = None) -> FinalizeRequest:
        return FinalizeRequest(
            self.value, self.ref, receipt or self.receipt, self.proof
        )

    def finalize(self, receipt: CompletionReceipt | None = None) -> FinalizeResult:
        """Run the fenced v2 finalizer on a fresh connection."""
        db = raw(self.path)
        try:
            return finalize_a2_workset_fenced(db, self.receipts, self.request(receipt))
        finally:
            db.close()

    def query(self, sql: str, args: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        db = raw(self.path)
        try:
            return [tuple(r) for r in db.execute(sql, args)]
        finally:
            db.close()

    def row(self) -> tuple[Any, ...]:
        return self.query(ROW)[0]

    def files(self) -> list[str]:
        root = self.receipts._root
        return sorted(p.name for p in root.rglob("*") if p.is_file())

    def snapshot(self) -> tuple[Any, ...]:
        tables = [self.query(f"SELECT * FROM phase1_{n}") for n in TABLES]
        return (self.query(ROW), tables, self.files())

    def owner(self) -> str | None:
        db = raw(self.path)
        try:
            return workset_owner(db, self.ref.result_id)
        finally:
            db.close()

    def flip_payload(self, data_id_like: str) -> None:
        """Change one byte of a saved semantic payload (same length)."""
        ((data_id, payload),) = self.query(
            "SELECT data_id, payload FROM phase1_semantic_data WHERE data_id LIKE ?",
            (data_id_like,),
        )
        self.edit(
            "UPDATE phase1_semantic_data SET payload = ? WHERE data_id = ?",
            (payload.replace(b"2", b"3", 1), data_id),
        )

    def edit(self, sql: str, args: tuple[Any, ...] = ()) -> None:
        db = raw(self.path)
        try:
            db.execute(sql, args)
        finally:
            db.close()

    def close(self) -> None:
        self.store.close()


def _saved(
    ref: ResultRef,
    payload: bytes,
    proof: AttemptProof,
    status: TerminalStatus,
    limits: tuple[Limitation, ...],
) -> StageResult:
    data = SemanticDataRef(
        "data-" + ref.result_id[-12:],
        ref.kind,
        ref.schema_version,
        sha256(payload).hexdigest(),
        len(payload),
    )
    return result_for(
        stage_identity(),
        result_id=ref.result_id,
        kind=ref.kind,
        schema_version=ref.schema_version,
        attempt=proof.attempt_id,
        status=status,
        limitations=limits,
        semantic_data_ref=data,
    )


def _accepted(ref: ResultRef, saved: StageResult, proof: AttemptProof):
    meta = stage_metadata(saved)
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
        writer=proof,
    )


def publish_root(
    db: sqlite3.Connection,
    seq: int,
    proof: AttemptProof,
    ref: ResultRef,
    payload: bytes,
    status: TerminalStatus = COMPLETE,
    limits: tuple[Limitation, ...] = (),
) -> None:
    """Store payload bytes, the saved result and the accepted-stage rows."""
    saved = _saved(ref, payload, proof, status, limits)
    data = saved.semantic_data_ref
    if data is None:
        pytest.fail("fixture result needs a semantic reference")
    insert_row(
        db,
        "phase1_semantic_data",
        {
            "data_id": data.data_id,
            "kind": data.kind,
            "schema_version": data.schema_version,
            "sha256": data.sha256,
            "byte_count": data.byte_count,
            "payload": payload,
        },
    )
    publish(db, _accepted(ref, saved, proof), seq, saved)


def prepared_payload(index: int, limits: bool) -> bytes:
    """Return canonical ``prepared@2`` bytes. ``limits`` makes it INCOMPLETE."""
    changes: dict[str, Any] = {"sent_at": 1_700_000_000 + index}
    if limits:
        changes = {"sent_at": None, "status": "incomplete"}
        changes["limitations"] = [limit_data()]
    return make(Prepared, prepared_data(**changes)).encode()


def build_world(tmp_path: Path, *, count: int = 2, held: bool = False) -> World:
    """
    Build a real Workset and its published v2 stage rows.

    With ``held``: root 0 is an INCOMPLETE ``prepared@2``, root 1 is an A2
    held disposition, and the Workset also has one Intake-held entry.
    """
    path = tmp_path / "e2e.sqlite"
    store = h.store(path)
    value, saved, _owner, _selections = c.admit(store, count=count, held=held)
    db = raw(path)
    migrate_schema4_to_v5(db, GATE)
    ref = ResultRef(saved.result_id, saved.kind, saved.schema_version)
    proof = AttemptProof(
        execution_id="exec-a1",
        attempt_id="a1",
        claim_key=workset_claim_key(ref.result_id),
        claim_token_sha256=hexd("c"),
    )
    seq = acquire_claim(db, proof)
    if seq is None:
        pytest.fail("v2 claim must be acquired")
    roots: list[TerminalRoot] = []
    prepared: list[ResultRef] = []
    for index in range(count):
        is_held = held and index == count - 1
        partial = held and index == 0
        kind, version = (HELD_KIND, "1") if is_held else ("prepared", "2")
        result = accepted_ref(str(index + 1), kind, version)
        payload = b"{}" if is_held else prepared_payload(index, partial)
        lims = (Limitation("time_unknown", CANARY),) if (partial or is_held) else ()
        if is_held:
            lims = (Limitation("source_evidence_unavailable", CANARY),)
        status = INCOMPLETE if lims else COMPLETE
        publish_root(db, seq, proof, result, payload, status, lims)
        if not is_held:
            prepared.append(result)
        roots.append(
            TerminalRoot(
                workset_selection_index=index,
                result=result,
                disposition="held" if is_held else "prepared",
                status=status,
                limitations=lims,
                selection=value.selections[index],
            )
        )
    db.close()
    (tmp_path / "proofs").mkdir()
    receipt = CompletionReceipt.build(
        workset=ref,
        status=INCOMPLETE if held else COMPLETE,
        policy_version="policy-1",
        roots=tuple(roots),
        intake_held_count=len(value.held),
    )
    return World(
        path, store, value, ref, proof, ReceiptStore(tmp_path / "proofs"),
        receipt, prepared,
    )  # fmt: skip


class SqliteLoader:
    """A3 persistence double: raw payload bytes from the real table."""

    def __init__(self, path: Path) -> None:
        self.path = path

    async def load_semantic_data(self, reference: SemanticDataRef) -> object:
        db = raw(self.path)
        try:
            row = db.execute(
                "SELECT payload FROM phase1_semantic_data WHERE data_id = ?",
                (reference.data_id,),
            ).fetchone()
        finally:
            db.close()
        return b"" if row is None else bytes(row[0])


@dataclass(frozen=True)
class A3View:
    values: tuple[Prepared, ...]
    hold: V2Hold | None
    saved: dict[str, StageResult]


def a3_read(world: World) -> A3View:
    """Load the prepared@2 family through the real A3 loader and adapter."""
    engine = create_engine(f"sqlite:///{world.path}")
    saved: dict[str, StageResult] = {}
    try:
        with engine.connect() as connection:
            for ref in world.prepared:
                query = select(STAGE_RESULTS).where(
                    STAGE_RESULTS.c.result_id == ref.result_id
                )
                found = connection.execute(query).mappings().first()
                if found is None:
                    pytest.fail("accepted stage row is missing")
                saved[ref.result_id] = result_from_row(found)
    finally:
        engine.dispose()
    refs = tuple(world.prepared)
    values = asyncio.run(load_values(SqliteLoader(world.path), refs, saved, Prepared))
    hold = admit_upstream((ref, saved[ref.result_id]) for ref in refs)
    return A3View(values, hold, saved)


def error_text(error: BaseException) -> str:
    """Return every text form of ``error``, its chain and its traceback."""
    parts = ["".join(traceback.format_exception(error)), str(error), repr(error)]
    parts.append(repr(error.args))
    return "\n".join(parts)


def check_clean(error: BaseException) -> None:
    check(CANARY not in error_text(error), "canary leaked into an exception")
    check(error.__cause__ is None, "raw error must not chain")
