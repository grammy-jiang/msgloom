"""C0-06 NativeRelations: scoped hypotheses, never facts."""

from __future__ import annotations

from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.relations import NativeRelations
from tests.a2_kedro.helpers import check


def node(node_id: str, scope: str = "t1", kind: str = "thread") -> dict[str, str]:
    return {"scope_kind": kind, "scope_id": scope, "node_id": node_id}


def rel(
    kind: str, src: dict[str, str], dst: dict[str, str], **kw: Any
) -> dict[str, Any]:
    return {"kind": kind, "source": src, "target": dst, "basis": "hdr", **kw}


def build(nodes: list[dict[str, str]], rels: list[dict[str, Any]]) -> NativeRelations:
    def nk(n: dict[str, str]) -> tuple[str, str, str]:
        return (n["scope_kind"], n["scope_id"], n["node_id"])

    def rk(r: dict[str, Any]) -> tuple[Any, ...]:
        return (r["kind"], nk(r["source"]), nk(r["target"]))

    return NativeRelations.model_validate(
        {
            "nodes": tuple(sorted(nodes, key=nk)),
            "relations": tuple(sorted(rels, key=rk)),
        }
    )


A, B, C = node("a"), node("b"), node("c")


def test_valid_record_round_trips_and_is_hypothesis() -> None:
    value = build(
        [A, B, C],
        [rel("reply_to", B, A), rel("ancestor", C, A), rel("reference", A, C)],
    )
    check(NativeRelations.decode(value.encode()) == value, "round trip")
    check(all(r.status == "hypothesis" for r in value.relations), "hypothesis")


def test_wire_form_is_pinned() -> None:
    data = build([A, B], [rel("reply_to", B, A)]).encode().decode()
    n = '{"node_id":"%s","scope_id":"t1","scope_kind":"thread"}'
    expected = (
        '{"header":{"kind":"native_relations","profile":"a2-c0-provisional-1",'
        '"version":"1"},"nodes":[' + n % "a" + "," + n % "b" + "],"
        '"relations":[{"basis":"hdr","kind":"reply_to","source":'
        + n % "b"
        + ',"status":"hypothesis","target":'
        + n % "a"
        + "}]}"
    )
    check(data == expected, "provisional wire form changed")


def test_same_thread_id_in_other_scope_does_not_relate() -> None:
    other = node("a", scope="t2")
    with pytest.raises(ValueError, match="crosses scopes"):
        build([A, B, other], [rel("reply_to", B, other)])
    with pytest.raises(ValueError, match="crosses scopes"):
        build([A, B], [rel("reply_to", B, other)])
    with pytest.raises(ValueError, match="not declared"):
        build([A, B], [rel("reply_to", B, node("zz"))])
    mailbox_a = node("a", scope="t1", kind="mailbox")
    with pytest.raises(ValueError, match="crosses scopes"):
        build([A, B, mailbox_a], [rel("reference", B, mailbox_a)])
    check(A != other and A != mailbox_a, "nodes differ by scope")


def test_negative_relations() -> None:
    with pytest.raises(ValueError, match="itself"):
        build([A], [rel("reference", A, A)])
    with pytest.raises(ValueError, match="duplicate relation"):
        build([A, B], [rel("reply_to", B, A), rel("reply_to", B, A)])
    with pytest.raises(ValueError, match="not declared"):
        build([A], [rel("reply_to", A, B)])
    with pytest.raises(ValueError, match="not declared"):
        build([B], [rel("reply_to", A, B)])
    with pytest.raises(ValueError, match="duplicate node"):
        build([A, A], [])
    with pytest.raises(ValueError, match="cycle"):
        build([A, B], [rel("ancestor", A, B), rel("ancestor", B, A)])
    with pytest.raises(ValueError, match="cycle"):
        build(
            [A, B, C],
            [rel("reply_to", A, B), rel("ancestor", B, C), rel("reply_to", C, A)],
        )
    for bad in ({"kind": "forward"}, {"status": "fact"}, {"basis": ""}, {"x": 1}):
        with pytest.raises(ValueError):
            build([A, B], [{**rel("reply_to", B, A), **bad}])


def test_reference_cycle_is_a_legal_hypothesis() -> None:
    build([A, B], [rel("reference", A, B), rel("reference", B, A)])


def test_unknown_or_missing_scope_and_extra_fields() -> None:
    with pytest.raises(ValueError):
        build([node("a", kind="folder")], [])
    with pytest.raises(ValueError):
        NativeRelations.model_validate({"nodes": ({"node_id": "a"},)})
    with pytest.raises(ValueError):
        build([{**A, "scope_id": ""}], [])
    with pytest.raises(ValueError):
        NativeRelations.model_validate({"nodes": (A,), "extra": 1})
    with pytest.raises(ValueError):
        NativeRelations.model_validate({"nodes": ({**A, "extra": 1},)})


def test_order_is_canonical() -> None:
    with pytest.raises(ValueError, match="not sorted"):
        NativeRelations.model_validate({"nodes": (B, A)})
    with pytest.raises(ValueError, match="not sorted"):
        NativeRelations.model_validate(
            {
                "nodes": (A, B),
                "relations": (rel("reply_to", B, A), rel("ancestor", B, A)),
            }
        )


def test_decode_is_strict() -> None:
    good = build([A, B], [rel("reply_to", B, A)]).encode()
    for bad in (
        good.replace(b'"hypothesis"', b'"fact"'),
        good.replace(b'"reply_to"', b'"forward"'),
        good + b" ",
        b'{"nodes":[],"nodes":[]}',
    ):
        with pytest.raises(A2ContractError):
            NativeRelations.decode(bad)
