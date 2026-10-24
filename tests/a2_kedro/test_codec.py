"""Bounded serialization and canonical digest tests."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.contracts.codec import (
    A2ContractError,
    A2Model,
    canonical_json_bytes,
    decode_canonical_json,
    domain_sha256,
    sha256_hex,
)
from tests.a2_kedro.helpers import check


def test_canonical_bytes_sorted_compact_utf8() -> None:
    data = canonical_json_bytes({"b": 1, "a": ["é", None, True]})
    check(data == '{"a":["é",null,true],"b":1}'.encode(), "not canonical")


def test_round_trip_is_strict() -> None:
    data = canonical_json_bytes({"a": 1, "b": [1, 2]})
    check(decode_canonical_json(data) == {"a": 1, "b": [1, 2]}, "round trip")


@pytest.mark.parametrize(
    "payload",
    [
        b'{"b":1,"a":2}',
        b'{"a": 1}',
        b'{"a":1,"a":2}',
        b'{"a":NaN}',
        b'{"a":1.5}',
        b"\xff",
    ],
)
def test_noncanonical_payload_rejected(payload: bytes) -> None:
    with pytest.raises(A2ContractError):
        decode_canonical_json(payload)


def test_size_bound_applies_on_encode_and_decode() -> None:
    with pytest.raises(A2ContractError):
        canonical_json_bytes({"a": "x" * 100}, max_bytes=50)
    with pytest.raises(A2ContractError):
        decode_canonical_json(b'{"a":"' + b"x" * 100 + b'"}', max_bytes=50)


@pytest.mark.parametrize(
    "value", [1.5, float("nan"), {1: "a"}, {"a": {1, 2}}, object()]
)
def test_non_json_values_rejected(value: object) -> None:
    with pytest.raises(A2ContractError):
        canonical_json_bytes(value)


def test_depth_bound() -> None:
    value: object = 1
    for _ in range(40):
        value = [value]
    with pytest.raises(A2ContractError):
        canonical_json_bytes(value)


def test_domain_separation_and_nul_guard() -> None:
    a = domain_sha256("one@1", {"k": 1})
    b = domain_sha256("two@1", {"k": 1})
    check(a != b, "domains must separate digests")
    check(a == sha256_hex(b"one@1\x00" + canonical_json_bytes({"k": 1})), "formula")
    with pytest.raises(A2ContractError):
        domain_sha256("bad\x00domain", {})


def test_model_rejects_oversized_text_unknown_field_and_mutation() -> None:
    class Sample(A2Model):
        name: str

    with pytest.raises(ValueError):
        Sample(name="x" * 2049)
    with pytest.raises(ValueError):
        Sample.model_validate({"name": "ok", "extra": 1})
    with pytest.raises(ValueError):
        Sample.model_validate({"name": 5})
    sample = Sample(name="ok")
    assign = setattr
    with pytest.raises(ValueError):
        assign(sample, "name", "other")
