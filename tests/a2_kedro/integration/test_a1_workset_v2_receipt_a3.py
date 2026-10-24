"""
C0-20b: real A1 Workset -> v2 accepted stages -> receipt finalizer -> A3 v2 read.

One ``tmp_path`` SQLite file per test. The Workset, its stored selections and
its processing claim come from the real Phase 1 helpers. The A3 side is the
real ``load_values`` and ``admit_upstream`` over the saved rows, read through
fresh connections. Known production gaps are strict ``xfail`` cases.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from msgloom import triage_input
from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt, TerminalRoot
from msgloom.persistence.a2_producer_binding import A2ProducerFenceError
from msgloom.persistence.a2_receipt_errors import A2ReceiptError
from msgloom.persistence.a2_registry import (
    build_a2_result_schema_registry,
    build_a2_semantic_registry,
)
from msgloom.persistence.codecs import decode_result_refs
from msgloom.persistence.errors import IncompatibleSchemaError
from msgloom.persistence.store import Phase1Store
from msgloom.preparation_pipeline.intake_models import workset_claim_key
from msgloom.triage_input.adapter_v2 import HOLD_CODE, V2Hold
from msgloom.triage_input.codec_v2 import DigestMismatchError
from tests.a2_kedro.helpers import accepted_ref, check
from tests.a2_kedro.integration.helpers_c0_20b import (
    CANARY,
    COMPLETE,
    INCOMPLETE,
    A3View,
    World,
    a3_read,
    build_world,
    check_clean,
)
from tests.a2_kedro.test_c0_14c import make_world as make_v1_world
from tests.a2_kedro.test_c0_14c import row_of, v1_finalize, v2_finalize
from tests.persistence.test_a2_schema_fixtures import build_schema5

Factory = Callable[..., World]
STAGE_COLUMNS = (
    "SELECT status, canonical_sha256, canonical_byte_count "
    "FROM phase1_a2_accepted_stages WHERE logical_key = ?"
)


@pytest.fixture
def worlds(tmp_path: Path) -> Iterator[Factory]:
    made: list[World] = []

    def make(name: str = "w", **kwargs: Any) -> World:
        root = tmp_path / name
        root.mkdir()
        made.append(build_world(root, **kwargs))
        return made[-1]

    yield make
    for world in made:
        world.close()


def claim_inputs(world: World) -> tuple[Any, ...]:
    rows = world.query(
        "SELECT required_inputs FROM phase1_work_claims WHERE claim_key = ?",
        (workset_claim_key(world.ref.result_id),),
    )
    check(len(rows) == 1, "exactly one processing claim")
    return decode_result_refs(rows[0][0])


def terminal_refs(world: World) -> list[str]:
    return [item["result_id"] for item in json.loads(world.row()[2])]


def refuse(world: World, receipt: CompletionReceipt, reason: str) -> A2ContractError:
    """Check a finalize refusal: fixed reason, nothing written, still pending."""
    before = world.snapshot()
    with pytest.raises(A2ContractError) as caught:
        world.finalize(receipt)
    error = caught.value
    found = getattr(error, "reason", "")
    check(found == reason, f"expected {reason}, got {found}")
    check(str(error) == reason, "message is the fixed reason only")
    check_clean(error)
    check(world.snapshot() == before, "a refusal must change nothing")
    check(world.row()[0] == "pending", "row stays pending")
    check(world.files() == [], "no proof file")
    return error


def drop_last_root(world: World) -> CompletionReceipt:
    return CompletionReceipt.build(
        workset=world.ref,
        status=COMPLETE,
        policy_version="policy-1",
        roots=world.receipt.roots[:-1],
    )


def extra_root(world: World) -> CompletionReceipt:
    extra = TerminalRoot(
        workset_selection_index=len(world.receipt.roots),
        result=accepted_ref("7", "prepared", "2"),
        disposition="prepared",
        status=COMPLETE,
        selection=world.value.selections[0],
    )
    return CompletionReceipt.build(
        workset=world.ref,
        status=COMPLETE,
        policy_version="policy-1",
        roots=(*world.receipt.roots, extra),
    )


# -- 1. happy path -------------------------------------------------------------


def test_workset_claim_has_real_required_inputs(worlds: Factory) -> None:
    world = worlds()
    check(claim_inputs(world) == (world.ref,), "required_inputs names the Workset")
    check(len(world.value.selections) == 2, "real frozen selections")
    kinds = world.query("SELECT kind, acceptable FROM phase1_stage_results")
    check(("collected_selection", 1) in kinds, "real selection result is stored")
    check(("preparation_intake_workset", 1) in kinds, "real Workset result is stored")


def test_complete_workset_finalizes_and_a3_reads_v2(worlds: Factory) -> None:
    world = worlds()
    check(world.row()[0] == "pending", "row starts pending")
    check(world.finalize().outcome == "finalized", "first finalize")
    state, status, _refs, token, execution, attempt = world.row()
    check((state, status) == ("terminal", "complete"), "terminal COMPLETE")
    check((execution, attempt) == ("exec-a1", "a1"), "producer recorded")
    check(token == world.proof.claim_token_sha256, "claim digest recorded")
    check(terminal_refs(world) == [r.result_id for r in world.prepared], "refs")
    check(len(world.files()) == 1, "one proof file")
    check(world.receipts.get_receipt_proof(world.ref) is not None, "proof readable")
    check(world.owner() == "v2", "v2 owner")
    check_a3_facts(world, a3_read(world))


def check_a3_facts(world: World, view: A3View) -> None:
    check(len(view.values) == len(world.prepared), "one value per prepared root")
    for ref, value in zip(world.prepared, view.values, strict=True):
        ((row_status, row_sha, row_size),) = world.query(
            STAGE_COLUMNS, (ref.result_id,)
        )
        payload = value.encode()
        check(sha256(payload).hexdigest() == row_sha, "payload sha equals stage row")
        check(len(payload) == row_size, "payload size equals stage row")
        check(value.status.value == row_status, "status equals stage row")
        check(view.saved[ref.result_id].status is value.status, "saved status")
    check(isinstance(view.hold, V2Hold), "A3 holds v2 upstream")
    check(view.hold is not None and view.hold.status is INCOMPLETE, "hold status")


# -- 2. held source ------------------------------------------------------------


def test_held_workset_finalizes_incomplete_and_a3_keeps_limitations(
    worlds: Factory,
) -> None:
    world = worlds(held=True)
    check(
        world.receipt.status is INCOMPLETE and world.receipt.intake_held_count == 1, "R"
    )
    check(world.finalize().outcome == "finalized", "held receipt finalizes")
    check(world.row()[:2] == ("terminal", "incomplete"), "terminal INCOMPLETE")
    view = a3_read(world)
    check_a3_facts(world, view)
    check(all(v.status is INCOMPLETE for v in view.values), "A3 sees INCOMPLETE")
    hold = view.hold
    if hold is None:
        pytest.fail("A3 must hold v2 upstream")
    codes = {item.code for item in hold.limitations}
    check(codes == {"time_unknown", HOLD_CODE}, "limitation propagated to A3")
    stage = world.query("SELECT status FROM phase1_a2_accepted_stages ORDER BY 1")
    check(all(row == ("incomplete",) for row in stage), "held stages INCOMPLETE")


def test_held_workset_cannot_claim_complete(worlds: Factory) -> None:
    world = worlds(held=True)
    roots = world.receipt.roots
    with pytest.raises(ValueError, match="status conflicts"):
        CompletionReceipt.build(
            workset=world.ref, status=COMPLETE, policy_version="p", roots=roots
        )
    bare = roots[-1].model_dump(mode="json") | {"limitations": []}
    with pytest.raises(ValueError):
        TerminalRoot.model_validate_json(json.dumps(bare))
    check(world.row()[0] == "pending", "nothing finalized")


# -- 3. receipt does not cover the Workset -------------------------------------


@pytest.mark.parametrize(
    ("make", "reason"),
    [
        (drop_last_root, "receipt-not-covering-workset"),
        (extra_root, "stage-unproven"),
    ],
)
def test_uncovered_receipt_is_refused_and_row_stays_pending(
    worlds: Factory, make: Callable[[World], CompletionReceipt], reason: str
) -> None:
    world = worlds()
    error = refuse(world, make(world), reason)
    check(isinstance(error, A2ReceiptError), "typed receipt error")
    check(world.receipts.get_receipt_proof(world.ref) is None, "not ready: no proof")
    check(world.finalize().outcome == "finalized", "the covering receipt works")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "missing A3 hook: load_values/admit_upstream and _TriageIOMixin never "
        "check that the Workset row is terminal or that a receipt proof exists"
    ),
)
def test_a3_refuses_upstream_of_a_pending_workset(worlds: Factory) -> None:
    world = worlds()
    refuse(world, drop_last_root(world), "receipt-not-covering-workset")
    with pytest.raises(Exception):  # noqa: B017 (any typed not-ready refusal)
        a3_read(world)


# -- 4. tampered accepted stage ------------------------------------------------

ACCEPTED = "UPDATE phase1_a2_accepted_stages SET "
TAMPER = (
    (
        ACCEPTED + "canonical_sha256 = ? WHERE logical_key = ?",
        "accepted-columns-mismatch",
    ),
    (ACCEPTED + "status = 'incomplete' WHERE logical_key = ?", "stored-record-corrupt"),
    (
        "UPDATE phase1_stage_results SET status = 'incomplete' WHERE result_id = ?",
        "stage-result-mismatch",
    ),
)


@pytest.mark.parametrize(("sql", "reason"), TAMPER)
def test_tampered_stage_is_refused_at_recheck(
    worlds: Factory, sql: str, reason: str
) -> None:
    world = worlds()
    key = world.prepared[0].result_id
    world.edit(sql, ("0" * 64, key) if sql.count("?") == 2 else (key,))
    before = world.snapshot()
    with pytest.raises(A2ContractError) as caught:
        world.finalize()
    check(getattr(caught.value, "reason", "") == reason, "expected reason")
    check(str(caught.value) == reason, "fixed reason only")
    check_clean(caught.value)
    check(world.snapshot() == before, "nothing written")
    check(world.row()[0] == "pending" and world.files() == [], "pending, no file")


# -- 5. idempotent replay ------------------------------------------------------


def test_identical_finalize_replays_without_a_second_write(worlds: Factory) -> None:
    world = worlds()
    first = world.finalize()
    after_first = world.snapshot()
    again = world.finalize()
    check((first.outcome, again.outcome) == ("finalized", "replayed"), "outcomes")
    check(world.snapshot() == after_first, "no row change and no second file")
    check(len(world.files()) == 1, "one proof file")
    check_a3_facts(world, a3_read(world))


# -- 6. v1 coexistence ---------------------------------------------------------


def test_v1_terminalization_still_works_on_the_same_schema(tmp_path: Path) -> None:
    world = make_v1_world(tmp_path)
    try:
        check(row_of(world.path)[0][0] == "pending", "pending before")
        v1_finalize(world)
        row = row_of(world.path)[0]
        check(row[:2] == ("terminal", "incomplete"), "v1 terminal row")
        check(len(decode_result_refs(row[2])) == len(world.refs), "v1 refs kept")
        v1_finalize(world)
        check(row_of(world.path)[0] == row, "v1 replay is idempotent")
        with pytest.raises(A2ProducerFenceError) as caught:
            v2_finalize(world)
        check(caught.value.reason == "legacy-finalized", "v2 writer fenced out")
        check(row_of(world.path)[0] == row, "v2 refusal changed nothing")
    finally:
        world.store.close()


# -- 7. PII --------------------------------------------------------------------


def test_canary_never_reaches_exception_text_or_repr(worlds: Factory) -> None:
    world = worlds(held=True)
    check(CANARY in world.receipt.model_dump_json(), "canary is in the input")
    check(CANARY not in repr(world.request()), "request repr hides data")
    world.edit(
        "UPDATE phase1_a2_accepted_stages SET canonical_sha256 = ? "
        "WHERE logical_key = ?",
        ("0" * 64, world.prepared[0].result_id),
    )
    with pytest.raises(A2ContractError) as caught:
        world.finalize()
    check_clean(caught.value)


def test_canary_never_reaches_a3_loader_errors(worlds: Factory) -> None:
    world = worlds(held=True)
    world.finalize()
    key = world.prepared[0].result_id
    world.flip_payload("%" + key[-12:])
    with pytest.raises(DigestMismatchError) as caught:
        a3_read(world)
    check_clean(caught.value)
    check(caught.value.__context__ is None, "no implicit context")


# -- known production gaps ------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    raises=IncompatibleSchemaError,
    reason=(
        "missing hook: Phase1Store/initialize_schema (schema_store.py) rejects "
        "a schema 5 file, so A3 has no A2-aware persistence over finalized rows"
    ),
)
def test_a3_real_store_opens_a_finalized_schema5_file(tmp_path: Path) -> None:
    path = build_schema5(tmp_path / "gap.sqlite")
    Phase1Store(
        f"sqlite:///{path}",
        build_a2_result_schema_registry(),
        build_a2_semantic_registry(),
    )


@pytest.mark.xfail(
    strict=True,
    reason=(
        "missing hook: no A3 builder for triage_input@2 from finalized rows "
        "(triage_input.build_triage_input is v1-only; no build_triage_input_v2)"
    ),
)
def test_a3_builds_triage_input_v2_from_finalized_rows() -> None:
    builder = getattr(triage_input, "build_triage_input_v2", None)
    check(builder is not None, "build_triage_input_v2 does not exist")
