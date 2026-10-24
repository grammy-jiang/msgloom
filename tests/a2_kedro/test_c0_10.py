"""C0-10 a2_completion_receipt@2: structural integrity, no DB claim logic."""

from __future__ import annotations

import json
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError, canonical_model_bytes
from msgloom.a2_kedro.contracts.receipt import (
    CompletionReceipt,
    ResultClaimProof,
    TerminalRoot,
    TransitionBatch,
    acceptance_index,
)
from msgloom.contracts import Limitation, ResultRef, TerminalStatus
from msgloom.preparation_pipeline.intake_models import IntakeSelection
from tests.a2_kedro.helpers import (
    WORKSET_REF,
    accepted_ref,
    check,
    proof,
    workset,
)
from tests.a2_kedro.test_held_receipt import held_ref, prepared_ref, receipt, terminal

COMPLETE, INCOMPLETE = TerminalStatus.COMPLETE, TerminalStatus.INCOMPLETE
PARTIAL = (Limitation("partial", "d"),)


def batch_for(ws: Any, char: str = "3") -> TransitionBatch:
    return TransitionBatch(
        transitions=ws.transitions,
        result=accepted_ref(char, "prepared_transitions", "2"),
        status=COMPLETE,
    )


def proofs_for(*refs: ResultRef) -> tuple[ResultClaimProof, ...]:
    return tuple(
        ResultClaimProof(result=ref, proof=proof(f"attempt-{i}"))
        for i, ref in enumerate(refs)
    )


def complete_receipt() -> tuple[Any, CompletionReceipt]:
    ws = workset(2, transitions=1)
    roots = (terminal(ws, 0, prepared_ref("1")), terminal(ws, 1, prepared_ref("2")))
    batch = batch_for(ws)
    results = (*(root.result for root in roots), batch.result)
    return ws, receipt(roots, transition_batch=batch, claim_proofs=proofs_for(*results))


def rejects(match: str, **kw: Any) -> None:
    with pytest.raises(ValueError, match=match):
        receipt(**kw)


def test_complete_receipt_is_positive_and_canonical() -> None:
    ws, good = complete_receipt()
    good.validate_against(ws, WORKSET_REF)
    good.require_claim_proofs()
    check(good.status is COMPLETE, "complete")
    check(len(good.roots) == len(ws.selections), "one root per occurrence")
    again = CompletionReceipt.model_validate_json(good.model_dump_json())
    check(again == good, "JSON round trip")
    check(canonical_model_bytes(again) == canonical_model_bytes(good), "bytes")
    check(again.digest() == good.digest(), "digest is stable")
    wire = json.loads(canonical_model_bytes(good))
    check("acceptance_index_sha256" in wire, "acceptance index on the wire")
    check(wire["transition_batch"] is not None, "transition batch on the wire")
    fields = set(wire["claim_proofs"][0]["proof"])
    check("claim_token_sha256" in fields, "claim proof holds a digest")
    check("secret-1" not in json.dumps(wire), "no raw claim token on the wire")


def test_incomplete_prepared_needs_explicit_limitations() -> None:
    ws = workset(2)
    one = terminal(ws, 0, prepared_ref("1"))
    two = terminal(ws, 1, prepared_ref("2"), INCOMPLETE)
    check(two.limitations == PARTIAL, "limitation kept on the root")
    done = receipt((one, two), status=INCOMPLETE)
    done.validate_against(ws, WORKSET_REF)
    kw: dict[str, Any] = {
        "workset_selection_index": 1,
        "result": prepared_ref("2"),
        "disposition": "prepared",
        "selection": ws.selections[1],
    }
    with pytest.raises(ValueError, match="conflicts with limitations"):
        TerminalRoot(status=INCOMPLETE, **kw)
    with pytest.raises(ValueError, match="conflicts with limitations"):
        TerminalRoot(status=COMPLETE, limitations=PARTIAL, **kw)
    with pytest.raises(ValueError, match="not sorted|duplicate"):
        two_same = PARTIAL * 2
        TerminalRoot(status=INCOMPLETE, limitations=two_same, **kw)


def test_missing_occurrence_is_rejected() -> None:
    ws = workset(2)
    one, two = (terminal(ws, i, prepared_ref(str(i + 1))) for i in range(2))
    with pytest.raises(A2ContractError, match="differ from frozen"):
        receipt((one,)).validate_against(ws, WORKSET_REF)
    rejects("frozen indexes in order", roots=(two,))
    with pytest.raises(A2ContractError, match="differ from frozen"):
        receipt((one, two)).validate_against(workset(3), WORKSET_REF)


def test_duplicate_occurrence_is_rejected() -> None:
    ws = workset(2)
    one = terminal(ws, 0, prepared_ref("1"))
    again = terminal(ws, 0, prepared_ref("2"))
    rejects("several terminals", roots=(one, again))
    same_result = terminal(ws, 1, prepared_ref("1"))
    rejects("several occurrences", roots=(one, same_result))


def test_prepared_and_held_overlap_is_rejected() -> None:
    ws = workset(2)
    prepared = terminal(ws, 0, prepared_ref("1"))
    held = terminal(ws, 0, held_ref("2"), INCOMPLETE)
    rejects("several terminals", roots=(prepared, held), status=INCOMPLETE)
    rejects("several terminals", roots=(held, prepared), status=INCOMPLETE)
    with pytest.raises(ValueError, match="wrong kind"):
        TerminalRoot(
            workset_selection_index=0,
            result=held_ref("2"),
            disposition="prepared",
            status=INCOMPLETE,
            limitations=PARTIAL,
            selection=ws.selections[0],
        )
    with pytest.raises(ValueError, match="wrong kind"):
        TerminalRoot(
            workset_selection_index=0,
            result=prepared_ref("1"),
            disposition="held",
            status=INCOMPLETE,
            limitations=PARTIAL,
            selection=ws.selections[0],
        )


def test_held_only_receipt_cannot_be_complete() -> None:
    ws = workset(2, held=1)
    held = tuple(terminal(ws, i, held_ref(str(i + 1)), INCOMPLETE) for i in range(2))
    rejects("conflicts with coverage", roots=held, status=COMPLETE)
    rejects("conflicts with coverage", status=COMPLETE, intake_held_count=1)
    only = receipt(held, status=INCOMPLETE, intake_held_count=1)
    only.validate_against(ws, WORKSET_REF)
    with pytest.raises(ValueError, match="held cannot be COMPLETE"):
        terminal(ws, 0, held_ref("1"), COMPLETE)
    prepared = terminal(ws, 0, prepared_ref("1"))
    rejects("conflicts with coverage", roots=(prepared,), intake_held_count=1)


def test_reordered_occurrences_are_rejected() -> None:
    ws = workset(2)
    one, two = (terminal(ws, i, prepared_ref(str(i + 1))) for i in range(2))
    rejects("frozen indexes in order", roots=(two, one))
    swapped = TerminalRoot(
        workset_selection_index=0,
        result=prepared_ref("1"),
        disposition="prepared",
        status=COMPLETE,
        selection=ws.selections[1],
    )
    other = TerminalRoot(
        workset_selection_index=1,
        result=prepared_ref("2"),
        disposition="prepared",
        status=COMPLETE,
        selection=ws.selections[0],
    )
    with pytest.raises(A2ContractError, match="differ from frozen"):
        receipt((swapped, other)).validate_against(ws, WORKSET_REF)


def test_extra_unknown_occurrence_is_rejected() -> None:
    ws = workset(2)
    roots = tuple(terminal(ws, i, prepared_ref(str(i + 1))) for i in range(2))
    big = workset(3)
    third = terminal(big, 2, prepared_ref("3"))
    with pytest.raises(A2ContractError, match="differ from frozen"):
        receipt((*roots, third)).validate_against(ws, WORKSET_REF)
    foreign = tuple(
        TerminalRoot(
            workset_selection_index=i,
            result=prepared_ref(str(i + 1)),
            disposition="prepared",
            status=COMPLETE,
            selection=big.selections[i + 1],
        )
        for i in range(2)
    )
    with pytest.raises(A2ContractError, match="differ from frozen"):
        receipt(foreign).validate_against(ws, WORKSET_REF)
    with pytest.raises(ValueError):
        TerminalRoot(
            workset_selection_index=1024,
            result=prepared_ref("1"),
            disposition="prepared",
            status=COMPLETE,
            selection=ws.selections[0],
        )


def test_deduplicated_selection_refs_are_a_trap() -> None:
    base = workset(2)
    twin = IntakeSelection(
        entry=base.selections[1].entry, result=base.selections[0].result
    )
    ws = workset(2, selections=(base.selections[0], twin))
    check(len(ws.selection_refs) == 1, "refs are de-duplicated")
    check(len(ws.selections) == 2, "occurrences are not")
    one = terminal(ws, 0, prepared_ref("1"))
    with pytest.raises(A2ContractError, match="differ from frozen"):
        receipt((one,)).validate_against(ws, WORKSET_REF)
    rejects("several occurrences", roots=(one, terminal(ws, 1, prepared_ref("1"))))
    both = receipt((one, terminal(ws, 1, prepared_ref("2"))))
    both.validate_against(ws, WORKSET_REF)
    check(ws.selections[0].entry != ws.selections[1].entry, "entries differ")
    first, second = both.roots[0].selection, both.roots[1].selection
    check(first is not None and second is not None, "incremental roots")
    if first is None or second is None:
        return
    check(first.result == second.result, "twin occurrences share one ref")


def test_transition_batch_is_required_when_the_workset_has_one() -> None:
    ws = workset(1, transitions=2)
    root = terminal(ws, 0, prepared_ref("1"))
    with pytest.raises(A2ContractError, match="missing or unexpected"):
        receipt((root,)).validate_against(ws, WORKSET_REF)
    with pytest.raises(A2ContractError, match="missing or unexpected"):
        receipt((root,), transition_batch=batch_for(ws)).validate_against(
            workset(1), WORKSET_REF
        )


def test_acceptance_index_binds_order_status_and_results() -> None:
    ws, good = complete_receipt()
    rejects(
        "acceptance index",
        roots=good.roots,
        transition_batch=good.transition_batch,
        acceptance_index_sha256="0" * 64,
    )
    rejects("String should match", roots=good.roots, acceptance_index_sha256="xyz")
    base = acceptance_index(good.roots, good.transition_batch)
    check(good.acceptance_index_sha256 == base, "build computes the index")
    wire = json.loads(good.model_dump_json())
    del wire["acceptance_index_sha256"]
    with pytest.raises(ValueError, match="acceptance_index_sha256"):
        CompletionReceipt.model_validate_json(json.dumps(wire))
    with pytest.raises(ValueError, match="acceptance_index_sha256"):
        CompletionReceipt.model_validate(wire)
    with pytest.raises(ValueError, match="acceptance index"):
        CompletionReceipt.model_validate_json(
            json.dumps({**wire, "acceptance_index_sha256": "0" * 64})
        )
    other = (terminal(ws, 0, prepared_ref("1")), terminal(ws, 1, prepared_ref("5")))
    check(acceptance_index(other, good.transition_batch) != base, "result bound")
    limited = (good.roots[0], terminal(ws, 1, prepared_ref("2"), INCOMPLETE))
    check(acceptance_index(limited, good.transition_batch) != base, "status bound")
    check(acceptance_index(good.roots, None) != base, "batch bound")
    first = good.roots[0]
    only = {
        "status alone": {"status": TerminalStatus.INCOMPLETE},
        "limitations alone": {"limitations": (Limitation("x", "y"),)},
        "disposition alone": {
            "disposition": "held" if first.disposition == "prepared" else "prepared"
        },
    }
    for label, update in only.items():
        changed = (first.model_copy(update=update), *good.roots[1:])
        check(acceptance_index(changed, good.transition_batch) != base, label)
    batch = good.transition_batch
    if batch is not None:
        flipped = batch.model_copy(update={"status": TerminalStatus.INCOMPLETE})
        check(acceptance_index(good.roots, flipped) != base, "batch status alone")
    other_batch = batch_for(ws, "9")
    check(acceptance_index(good.roots, other_batch) != base, "batch result bound")


def test_claim_proofs_are_structural_and_all_or_nothing() -> None:
    _ws, good = complete_receipt()
    results = [root.result for root in good.roots]
    batch = good.transition_batch
    check(batch is not None, "fixture has a batch")
    if batch is None:
        return
    results.append(batch.result)
    partial = proofs_for(*results[:2])
    rejects(
        "claim proofs differ",
        roots=good.roots,
        transition_batch=batch,
        claim_proofs=partial,
    )
    twice = proofs_for(*results, results[0])
    rejects(
        "duplicate claim proof",
        roots=good.roots,
        transition_batch=batch,
        claim_proofs=twice,
    )
    foreign = proofs_for(*results[:2], prepared_ref("7"))
    rejects(
        "claim proofs differ",
        roots=good.roots,
        transition_batch=batch,
        claim_proofs=foreign,
    )
    bare = receipt(good.roots, transition_batch=batch)
    with pytest.raises(A2ContractError, match="no claim proofs"):
        bare.require_claim_proofs()
    with pytest.raises(ValueError):
        ResultClaimProof.model_validate({"result": results[0], "proof": {"token": "t"}})
    names = set(ResultClaimProof.model_fields["proof"].annotation.model_fields)  # type: ignore[union-attr]
    check("claim_token_sha256" in names and "token" not in names, "digest only")


def test_receipt_shape_negative_cases() -> None:
    ws = workset(1)
    root = terminal(ws, 0, prepared_ref("1"))
    rejects("foreign workset", roots=(root,), workset=ResultRef("w", "other", "1"))
    old = TerminalRoot.model_validate_json(root.model_dump_json())
    check(old == root, "root round trip")
    data = json.loads(receipt((root,)).model_dump_json())
    for bad in ({**data, "extra": 1}, {**data, "status": "failed"}):
        with pytest.raises(ValueError):
            CompletionReceipt.model_validate_json(json.dumps(bad))
    stale = {
        **data,
        "roots": [{**data["roots"][0], "limitations": [{"code": "x", "detail": "y"}]}],
    }
    with pytest.raises(ValueError, match="conflicts with limitations"):
        CompletionReceipt.model_validate_json(json.dumps(stale))
    with pytest.raises(A2ContractError) as caught:
        receipt((root,)).validate_against(workset(2), WORKSET_REF)
    check(root.result.result_id not in str(caught.value), "message has no id")
