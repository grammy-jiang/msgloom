"""C0-08 scoped transition batch: non-droppable item and batch identity."""

from __future__ import annotations

from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.transition import (
    ItemProof,
    TransitionBatch,
    TransitionItem,
    batch_digest,
    verify_item_proof,
)
from msgloom.contracts import ResultRef
from tests.a2_kedro.helpers import check, hexd, transition_for

WS = ResultRef("ws-1", "preparation_intake_workset", "1")


def item(i: int, fact: str, **kw: Any) -> TransitionItem:
    base = TransitionItem.from_intake(
        i, transition_for(i + 1, fact), kw.pop("authority", "auth-1")
    )
    return TransitionItem.model_validate({**base.model_dump(), **kw})


def items(*facts: str) -> tuple[TransitionItem, ...]:
    return tuple(item(i, f) for i, f in enumerate(facts))


def batch(
    its: tuple[TransitionItem, ...] | None = None,
    ws: ResultRef = WS,
    code: str = "code-1",
    policy: str = "pol-1",
) -> TransitionBatch:
    return TransitionBatch.build(ws, code, policy, its or items("a", "b", "c"))


def renumber(its: list[TransitionItem]) -> tuple[TransitionItem, ...]:
    return tuple(i.model_copy(update={"ordinal": n}) for n, i in enumerate(its))


def test_round_trip_and_pinned_wire_names() -> None:
    value = batch()
    check(TransitionBatch.decode(value.encode()) == value, "round trip")
    data = value.model_dump(mode="json")
    check(
        sorted(data)
        == [
            "batch_sha256",
            "code_version",
            "header",
            "items",
            "policy_version",
            "workset",
        ],
        "batch field names",
    )
    check(
        sorted(data["items"][0])
        == [
            "authority",
            "entry",
            "fact_id",
            "kind",
            "ordinal",
            "scope_id",
            "scope_kind",
        ],
        "item field names",
    )


def test_identity_is_pinned_to_inputs() -> None:
    base = batch()
    check(len(base.batch_sha256) == 64, "digest shape")
    check(base.batch_sha256 == batch().batch_sha256, "deterministic")
    check(base.batch_sha256 != batch(code="code-2").batch_sha256, "code")
    check(base.batch_sha256 != batch(policy="pol-2").batch_sha256, "policy")
    other = ResultRef("ws-2", "preparation_intake_workset", "1")
    check(base.batch_sha256 != batch(ws=other).batch_sha256, "workset")


def test_removing_reordering_substituting_change_identity() -> None:
    its = list(items("a", "b", "c"))
    base = batch().batch_sha256
    seen = {base}
    variants = {
        "drop_last": renumber(its[:2]),
        "drop_first": renumber(its[1:]),
        "reorder": renumber([its[1], its[0], its[2]]),
        "reverse": renumber(its[::-1]),
        "substitute": renumber([its[0], item(1, "9"), its[2]]),
        "append": renumber([*its, item(3, "d")]),
    }
    for name, value in variants.items():
        digest = batch(value).batch_sha256
        check(digest not in seen, "identity unchanged by " + name)
        seen.add(digest)


@pytest.mark.parametrize(
    "update",
    [
        {"authority": "auth-2"},
        {"kind": "deletion"},
        {"scope_id": "other"},
        {"scope_kind": "other"},
        {"fact_id": hexd("9")},
    ],
)
def test_every_item_field_is_in_the_identity(update: dict[str, Any]) -> None:
    its = list(items("a", "b"))
    its[1] = its[1].model_copy(update=update)
    check(batch(tuple(its)).batch_sha256 != batch(items("a", "b")).batch_sha256, "x")
    check(its[1].digest() != items("a", "b")[1].digest(), "item digest")


def test_entry_is_in_the_identity() -> None:
    its = list(items("a", "b"))
    its[1] = its[1].model_copy(update={"entry": transition_for(9, "b").entry})
    check(batch(tuple(its)).batch_sha256 != batch(items("a", "b")).batch_sha256, "x")


def test_stored_identity_cannot_be_kept_after_tampering() -> None:
    good = batch()
    fields: dict[str, Any] = {
        "workset": good.workset,
        "code_version": good.code_version,
        "policy_version": good.policy_version,
        "items": good.items,
        "batch_sha256": good.batch_sha256,
    }
    its = list(good.items)
    tampered: list[dict[str, Any]] = [
        {"items": renumber(its[:2])},
        {"items": renumber([its[1], its[0], its[2]])},
        {"items": renumber([its[0], item(1, "9"), its[2]])},
        {"code_version": "code-2"},
        {"policy_version": "pol-2"},
        {"workset": ResultRef("ws-2", "preparation_intake_workset", "1")},
        {"batch_sha256": hexd("0")},
    ]
    for change in tampered:
        with pytest.raises(ValueError, match="identity does not match"):
            TransitionBatch(**{**fields, **change})


def test_structural_negatives() -> None:
    with pytest.raises(ValueError, match="duplicate fact"):
        batch(renumber([item(0, "a"), item(1, "a")]))
    with pytest.raises(ValueError, match="contiguous"):
        batch((item(0, "a"), item(2, "b")))
    with pytest.raises(ValueError, match="contiguous"):
        batch((item(1, "a"), item(0, "b")))
    with pytest.raises(ValueError, match="out of bounds"):
        TransitionBatch(
            workset=WS,
            code_version="c",
            policy_version="p",
            items=(),
            batch_sha256=batch_digest(WS, "c", "p", ()),
        )
    with pytest.raises(ValueError, match="workset schema"):
        batch(ws=ResultRef("ws", "prepared", "2"))
    with pytest.raises(ValueError):
        item(0, "a", kind="unknown")
    with pytest.raises(ValueError):
        item(0, "a", authority="")
    with pytest.raises(ValueError):
        TransitionItem.model_validate(
            {**items("a")[0].model_dump(mode="python"), "extra": 1}
        )
    with pytest.raises(ValueError):
        TransitionBatch.model_validate({**batch().__dict__, "extra": 1})


def test_item_proof_binds_item_position_and_batch() -> None:
    value = batch()
    for n, it in enumerate(value.items):
        verify_item_proof(value, it, value.proof(n))
    proof = value.proof(1)
    other = batch(code="code-2")
    with pytest.raises(A2ContractError, match="another batch"):
        verify_item_proof(other, other.items[1], proof)
    with pytest.raises(A2ContractError, match="does not match"):
        verify_item_proof(value, value.items[0], proof)
    swapped = value.items[1].model_copy(update={"authority": "auth-2"})
    with pytest.raises(A2ContractError, match="does not match"):
        verify_item_proof(value, swapped, proof)
    forged = ItemProof(**{**proof.model_dump(), "item_sha256": swapped.digest()})
    with pytest.raises(A2ContractError, match="not in the batch"):
        verify_item_proof(value, swapped, forged)
    shorter = ItemProof(**{**proof.model_dump(), "count": 2})
    with pytest.raises(A2ContractError, match="another batch"):
        verify_item_proof(value, value.items[1], shorter)
    with pytest.raises(A2ContractError, match="out of range"):
        value.proof(3)
    with pytest.raises(ValueError):
        ItemProof(**{**proof.model_dump(), "extra": 1})


def test_decode_rejects_tampered_bytes() -> None:
    data = batch().encode()
    for bad in (
        data.replace(b'"auth-1"', b'"auth-2"', 1),
        data.replace(b'"code-1"', b'"code-2"'),
        data + b" ",
        b'{"items":[],"items":[]}',
    ):
        with pytest.raises(A2ContractError):
            TransitionBatch.decode(bad)
