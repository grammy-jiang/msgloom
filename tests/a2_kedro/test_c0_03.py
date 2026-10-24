"""C0-03 ExtractedComponents: statuses, digests and bounded metadata."""

from __future__ import annotations

from typing import Any

import pytest

from msgloom.a2_kedro.contracts import extract
from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.extract import (
    ComponentEntry,
    ExtractedComponents,
    decode_metadata,
    encode_metadata,
)
from tests.a2_kedro.helpers import check, hexd


def comp(cid: str = "p", role: str = "primary", **kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "component_id": cid,
        "role": role,
        "status": "present",
        "reference": "saved/" + cid,
        "sha256": hexd("a"),
    }
    return {**base, **kw}


def record(*items: dict[str, Any]) -> ExtractedComponents:
    return ExtractedComponents.model_validate({"components": items or (comp(),)})


def test_all_roles_and_statuses_round_trip_canonically() -> None:
    items = (
        comp("p"),
        comp("a", "alternate", status="partial"),
        comp("t", "attachment", metadata=(("name", "x.pdf"), ("size", "9"))),
        comp("e", "embedded", status="unsupported"),
        comp("m", "attachment", status="missing", reference=None, sha256=None),
    )
    value = record(*items)
    data = value.encode()
    check(ExtractedComponents.decode(data) == value, "round trip")
    check(value.encode() == data, "stable bytes")
    check(value.header.kind == "extracted_components", "header kind")
    check(extract.KIND == "extracted_components", "kind constant")


def test_wire_field_names_are_pinned() -> None:
    data = record().encode().decode()
    check(
        data == '{"components":[{"component_id":"p","metadata":[],'
        '"reference":"saved/p","role":"primary","sha256":"' + hexd("a") + '",'
        '"status":"present"}],"header":{"kind":"extracted_components",'
        '"profile":"a2-c0-provisional-1","version":"1"}}',
        "provisional wire form changed",
    )


@pytest.mark.parametrize(
    "bad",
    [
        comp(status="unknown"),
        comp(role="inline"),
        comp(sha256="A" * 64),
        comp(sha256="a" * 63),
        comp(sha256="g" * 64),
        comp(reference=None),
        comp(sha256=None),
        comp(status="partial", reference=None),
        comp(status="missing"),
        comp(status="unsupported", sha256=None),
        comp(extra="x"),
        comp(metadata=(("b", "1"), ("a", "2"))),
        comp(metadata=(("a", "1"), ("a", "2"))),
        comp(metadata=(("a", "x" * 257),)),
        comp(metadata=tuple((f"k{i:02}", "v") for i in range(33))),
    ],
)
def test_bad_component_is_rejected(bad: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        record(bad)


def test_record_level_negatives() -> None:
    with pytest.raises(ValueError, match="duplicate component id"):
        record(comp("p"), comp("p", "alternate"))
    with pytest.raises(ValueError, match="primary"):
        record(comp("a", "alternate"))
    with pytest.raises(ValueError, match="primary"):
        record(comp("p"), comp("q"))
    with pytest.raises(ValueError):
        ExtractedComponents.model_validate({"components": (comp(),), "x": 1})
    with pytest.raises(ValueError, match="count"):
        ExtractedComponents.model_validate({"components": ()})
    many = [comp("p")] + [comp(f"a{i}", "attachment") for i in range(256)]
    with pytest.raises(ValueError, match="count"):
        record(*many)
    with pytest.raises(ValueError):
        ExtractedComponents.model_validate(
            {
                "header": {"kind": "zones", "version": "1"},
                "components": (comp(),),
            }
        )


def test_missing_component_stays_visible_and_unsupported_may_lack_bytes() -> None:
    gone = comp("m", "attachment", status="missing", reference=None, sha256=None)
    value = record(comp(), gone)
    check(len(value.components) == 2, "missing entry is kept")
    ComponentEntry.model_validate(
        comp("u", "embedded", status="unsupported", reference=None, sha256=None)
    )


def test_metadata_codec_strict() -> None:
    data = encode_metadata({"b": "2", "a": "1"})
    check(data == b'{"a":"1","b":"2"}', "canonical metadata")
    check(decode_metadata(data) == (("a", "1"), ("b", "2")), "decode")
    bad_inputs = [
        b'{"a":"1","a":"2"}',
        b'{"b":"1","a":"2"}',
        b'{"a": "1"}',
        b'{"a":1}',
        b'["a"]',
        b"{" + b'"k":"' + b"x" * 5000 + b'"}',
        b"\xff",
        b'{"a":1.5}',
    ]
    for item in bad_inputs:
        with pytest.raises(A2ContractError):
            decode_metadata(item)
    with pytest.raises(A2ContractError):
        encode_metadata({"a": 1})  # type: ignore[dict-item]
    with pytest.raises(A2ContractError):
        encode_metadata({"": "x"})
    with pytest.raises(A2ContractError):
        encode_metadata({f"k{i}": "x" * 256 for i in range(32)})


def test_decode_rejects_noncanonical_duplicate_and_extra() -> None:
    good = record().encode()
    with pytest.raises(A2ContractError):
        ExtractedComponents.decode(good.replace(b'"components"', b'"components" '))
    with pytest.raises(A2ContractError):
        ExtractedComponents.decode(b'{"a":1,"a":2}')
    with pytest.raises(A2ContractError):
        ExtractedComponents.decode(good.replace(b'"status"', b'"zzz":"1","status"'))
    with pytest.raises(A2ContractError):
        ExtractedComponents.decode(good.replace(b'"present"', b'"unknown"'))
    with pytest.raises(A2ContractError):
        ExtractedComponents.decode(b"x" * (4 * 1024 * 1024 + 1))
