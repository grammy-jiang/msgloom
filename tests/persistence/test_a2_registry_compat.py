"""
C0-21b: A2 v2 registry goldens and negatives; no database.

Golden bytes, digests and old-registry rows are hand-written literals.
Body validation is out of scope: ``A2HeaderCodec`` fixes only the envelope.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any, NamedTuple

import pytest
from pydantic import BaseModel

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.header import StageHeader
from msgloom.contracts import ResultSchemaRegistry, SemanticDataRef
from msgloom.persistence.a2_registry import (
    A2HeaderCodec,
    A2RegistryError,
    A2UnknownSchemaError,
    build_a2_result_schema_registry,
    build_a2_semantic_registry,
)
from msgloom.persistence.errors import (
    SemanticDataIntegrityError,
    SemanticDataReferenceError,
    SemanticDataTypeError,
    UnknownSemanticDataSchemaError,
)
from msgloom.persistence.semantic import SemanticDataRegistry

PROFILE = "a2-c0-provisional-1"

# Hand-written canonical bytes and SHA-256 digests, keyed by kind@version.
GOLDEN_BYTES: dict[str, bytes] = {
    "a2_completion_receipt@2": (
        b'{"body":{"n":1},"header":{"kind":"a2_completion_receipt",'
        b'"profile":"a2-c0-provisional-1","version":"2"}}'
    ),
    "a2_input_disposition@1": (
        b'{"body":{"n":1},"header":{"kind":"a2_input_disposition",'
        b'"profile":"a2-c0-provisional-1","version":"1"}}'
    ),
    "a2_result_manifest@1": (
        b'{"body":{"n":1},"header":{"kind":"a2_result_manifest",'
        b'"profile":"a2-c0-provisional-1","version":"1"}}'
    ),
    "extracted_components@1": (
        b'{"body":{"n":1},"header":{"kind":"extracted_components",'
        b'"profile":"a2-c0-provisional-1","version":"1"}}'
    ),
    "filter_result@2": (
        b'{"body":{"n":1},"header":{"kind":"filter_result",'
        b'"profile":"a2-c0-provisional-1","version":"2"}}'
    ),
    "frozen_source_selection@1": (
        b'{"body":{"n":1},"header":{"kind":"frozen_source_selection",'
        b'"profile":"a2-c0-provisional-1","version":"1"}}'
    ),
    "group_result@2": (
        b'{"body":{"n":1},"header":{"kind":"group_result",'
        b'"profile":"a2-c0-provisional-1","version":"2"}}'
    ),
    "native_relations@1": (
        b'{"body":{"n":1},"header":{"kind":"native_relations",'
        b'"profile":"a2-c0-provisional-1","version":"1"}}'
    ),
    "normalized_content@1": (
        b'{"body":{"n":1},"header":{"kind":"normalized_content",'
        b'"profile":"a2-c0-provisional-1","version":"1"}}'
    ),
    "parsed_parts@1": (
        b'{"body":{"n":1},"header":{"kind":"parsed_parts",'
        b'"profile":"a2-c0-provisional-1","version":"1"}}'
    ),
    "prepared@2": (
        b'{"body":{"n":1},"header":{"kind":"prepared",'
        b'"profile":"a2-c0-provisional-1","version":"2"}}'
    ),
    "prepared_transitions@2": (
        b'{"body":{"n":1},"header":{"kind":"prepared_transitions",'
        b'"profile":"a2-c0-provisional-1","version":"2"}}'
    ),
    "triage_input@2": (
        b'{"body":{"n":1},"header":{"kind":"triage_input",'
        b'"profile":"a2-c0-provisional-1","version":"2"}}'
    ),
    "zones@1": (
        b'{"body":{"n":1},"header":{"kind":"zones",'
        b'"profile":"a2-c0-provisional-1","version":"1"}}'
    ),
}
GOLDEN_SHA256: dict[str, str] = {
    "a2_completion_receipt@2": "41f81a1266d895264c375e374d5b06816fd352fb6a09d4264b6f2fe242c53163",
    "a2_input_disposition@1": "dbdb15a6cc0367a65750e8f9ea8dafddbdca0b1c9d1c74bbad463e8bcfe02b52",
    "a2_result_manifest@1": "d08b4ff273930d5469e9afa868e24a0aad58ab31b1ce65894a09dfccc2cc7022",
    "extracted_components@1": "66c475d7675f23c56a6044a532e8cab6aca82a2aeacfddf174f77e57965898e7",
    "filter_result@2": "d3ba37ad032cb1d009fb23da67c65ab7a09db762ff5953baf1bec97e65049584",
    "frozen_source_selection@1": "df5649fe03ae41fcce97cb833948cac1226d9d6b73ef6c1a095f96febd4b5a8a",
    "group_result@2": "8b63820c47fae8279b5cdf2650af4da76d80f6274dc2418a153645731a1b7300",
    "native_relations@1": "e16d0acf8fd4d4dcca900cba7705b20eb9cabae633a1cb02fb9fd9de8b40acbb",
    "normalized_content@1": "f3c438ac77ef73987a6ee3ab6ee6e2e82ba779fb7cdd0bead20bd12b9aea07b9",
    "parsed_parts@1": "d6ee65c599936fece61d2b0839bd5cc6afe21b5dba3390a8ca2a69668f1c3ff5",
    "prepared@2": "61eab63fd26a0fb46a03e297988735b7e58bc182714d85b5af8129f9c5fb740e",
    "prepared_transitions@2": "8b81bf6bb5efe2d9828c48d0f5426e84fa2cfd720a71d4d1aa599c3dd31ad9b4",
    "triage_input@2": "f9dcd8932e4644ca6d16bd8c689a934f0aad6fc309b1634b90bef1c35909b445",
    "zones@1": "ba171142610aaf7a1d28ba3ef7c0d0c5648bd90d5c47e37c8ff6d4f9a2c163c1",
}


class Golden(NamedTuple):
    kind: str
    version: str
    payload: bytes
    sha256: str

    @property
    def ref(self) -> SemanticDataRef:
        return SemanticDataRef(
            "d1", self.kind, self.version, self.sha256, len(self.payload)
        )

    def __str__(self) -> str:
        return f"{self.kind}@{self.version}"


GOLDENS = [
    Golden(*key.split("@"), GOLDEN_BYTES[key], GOLDEN_SHA256[key])  # type: ignore[arg-type]
    for key in GOLDEN_BYTES
]
ALL = pytest.mark.parametrize("g", GOLDENS, ids=str)

OLD_KIND_TEXT = (
    "ai_request ai_response ai_trace collected_selection derived_bytes "
    "filter_result group_result preparation_intake_workset prepared "
    "prepared_transitions report report_selection report_submission triage "
    "triage_input triage_input_part triage_part_state triage_rules "
    "working_context"
)
OLD_KINDS = OLD_KIND_TEXT.split()
OLD_RESULT_PAIRS = frozenset((kind, "1") for kind in OLD_KINDS)
# ``report_submission`` is the one old pair that needs no semantic data.
OLD_SEMANTIC_REQUIRED = OLD_RESULT_PAIRS - {("report_submission", "1")}
OLD_CODEC_ROWS = [
    ("collected_selection", "1", 33554432),
    ("preparation_intake_workset", "1", 4194304),
    ("prepared_transitions", "1", 4194304),
    ("derived_bytes", "1", 25165824),
    ("report_selection", "1", 2097152),
    ("report", "1", 8388608),
    ("report_submission", "1", 16777216),
    ("triage_input_part", "1", 4194304),
    ("triage_part_state", "1", 65536),
    ("prepared", "1", 16777216),
    ("filter_result", "1", 1048576),
    ("group_result", "1", 4194304),
    ("working_context", "1", 16777216),
    ("triage_rules", "1", 4194304),
    ("triage_input", "1", 67108864),
    ("triage", "1", 4194304),
    ("ai_request", "1", 4194304),
    ("ai_trace", "1", 1048576),
    ("ai_response", "1", 4194304),
]


def header(kind: str, version: str) -> dict[str, str]:
    return {"kind": kind, "profile": PROFILE, "version": version}


def envelope(kind: str, version: str) -> dict[str, Any]:
    return {"body": {"n": 1}, "header": header(kind, version)}


class Envelope(BaseModel):
    header: StageHeader
    body: dict[str, int]


def other_than(g: Golden) -> Golden:
    return next(x for x in GOLDENS if x != g)


@ALL
def test_golden_bytes_digest_and_reference(g: Golden) -> None:
    encoded = build_a2_semantic_registry().encode(
        "d1", g.kind, g.version, envelope(g.kind, g.version)
    )
    if encoded.payload != g.payload:
        pytest.fail("canonical bytes differ from the golden literal")
    if encoded.reference != g.ref:
        pytest.fail("reference differs from the golden literal")


@ALL
def test_golden_decodes_to_literal_value_and_round_trips(g: Golden) -> None:
    registry = build_a2_semantic_registry()
    value = registry.decode(g.ref, g.payload)
    if value != {
        "body": {"n": 1},
        "header": {"kind": g.kind, "profile": PROFILE, "version": g.version},
    }:
        pytest.fail("decoded value differs from the golden literal")
    if registry.encode_for_reference(g.ref, value).payload != g.payload:
        pytest.fail("strict round trip changed the bytes")


@ALL
def test_model_input_encodes_to_the_same_golden(g: Golden) -> None:
    model = Envelope(header=StageHeader(kind=g.kind, version=g.version), body={"n": 1})
    if A2HeaderCodec(g.kind, g.version).encode(model) != g.payload:
        pytest.fail("model input produced other bytes than mapping input")


def test_rich_body_golden_is_sorted_compact_utf8() -> None:
    value = {
        "header": header("zones", "1"),
        "body": {"z": [True, None, -2], "a": "é", "b": {}},
    }
    expected = (
        b'{"body":{"a":"\xc3\xa9","b":{},"z":[true,null,-2]},'
        b'"header":{"kind":"zones","profile":"a2-c0-provisional-1","version":"1"}}'
    )
    codec = A2HeaderCodec("zones", "1")
    if codec.encode(value) != expected:
        pytest.fail("rich body bytes differ from the golden literal")
    body = {"a": "é", "b": {}, "z": [True, None, -2]}
    if codec.decode(expected) != {"body": body, "header": header("zones", "1")}:
        pytest.fail("rich body decoded differently")


@ALL
def test_golden_under_another_pair_is_rejected(g: Golden) -> None:
    o = other_than(g)
    with pytest.raises(A2RegistryError):
        A2HeaderCodec(o.kind, o.version).decode(g.payload)
    with pytest.raises(A2RegistryError):
        build_a2_semantic_registry().encode(
            "d1", o.kind, o.version, envelope(g.kind, g.version)
        )
    forged = SemanticDataRef("d1", o.kind, o.version, g.sha256, len(g.payload))
    with pytest.raises(SemanticDataIntegrityError):
        build_a2_semantic_registry().decode(forged, g.payload)


def wire(bad_header: dict[str, Any]) -> bytes:
    """Return hand-ordered canonical bytes for a payload with ``bad_header``."""
    value = {"body": {}, "header": bad_header}
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


@ALL
def test_wrong_header_version_or_profile_is_rejected(g: Golden) -> None:
    codec = A2HeaderCodec(g.kind, g.version)
    good = {"kind": g.kind, "profile": PROFILE, "version": g.version}
    for bad in (
        {**good, "version": "999"},
        {**good, "profile": "other"},
        {**good, "version": int(g.version)},
        {**good, "extra": "x"},
        {**good, "kind": "unknown_kind"},
    ):
        with pytest.raises(A2RegistryError):
            codec.encode({"body": {}, "header": bad})
        with pytest.raises(A2ContractError):
            codec.decode(wire(bad))


@ALL
def test_wrong_payload_shape_is_rejected(g: Golden) -> None:
    registry = build_a2_semantic_registry()
    for bad in ({"body": {}}, {"header": None}, {"header": []}, {"header": "x"}):
        with pytest.raises(A2RegistryError):
            registry.encode("d1", g.kind, g.version, bad)
    for bad in ("text", b"bytes", ["header"], None, 7):
        with pytest.raises(SemanticDataTypeError):
            registry.encode("d1", g.kind, g.version, bad)
    for bad in (b"[]", b"null", b"7", b'"x"'):
        with pytest.raises(A2RegistryError):
            A2HeaderCodec(g.kind, g.version).decode(bad)


NON_CANONICAL = [{"n": 1.5}, {"n": float("nan")}, {1: "x"}, {"n": {1}}, {"n": b"r"}]


@pytest.mark.parametrize("value", NON_CANONICAL)
def test_non_canonical_data_is_rejected_on_encode(value: object) -> None:
    codec = A2HeaderCodec("zones", "1")
    with pytest.raises(A2ContractError):
        codec.encode({"header": header("zones", "1"), "body": value})


def test_over_deep_value_is_rejected_on_encode() -> None:
    body: Any = {}
    for _ in range(40):
        body = {"d": body}
    with pytest.raises(A2ContractError):
        A2HeaderCodec("zones", "1").encode(
            {"header": header("zones", "1"), "body": body}
        )


GOLDEN_ZONES = GOLDEN_BYTES["zones@1"]
HEADER_TEXT = b'{"kind":"zones","profile":"a2-c0-provisional-1","version":"1"}'


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b" " + GOLDEN_ZONES,
        GOLDEN_ZONES + b"\n",
        b"\xef\xbb\xbf" + GOLDEN_ZONES,
        GOLDEN_ZONES[:-1],
        GOLDEN_ZONES.replace(b",", b", "),
        b'{"header":' + HEADER_TEXT + b',"body":{"n":1}}',
        b'{"body":{"n":1},"body":{"n":1},"header":' + HEADER_TEXT + b"}",
        b'{"body":{"n":NaN},"header":' + HEADER_TEXT + b"}",
        b'{"body":{"n":Infinity},"header":' + HEADER_TEXT + b"}",
        b'{"body":{"n":1.0},"header":' + HEADER_TEXT + b"}",
        b'{"body":{"n":1e2},"header":' + HEADER_TEXT + b"}",
        b'{"body":{"n":"\\u00e9"},"header":' + HEADER_TEXT + b"}",
        b'{"body":{"n":"\xff"},"header":' + HEADER_TEXT + b"}",
        b"\xff\xfe",
    ],
    ids=[
        "empty",
        "leading-space",
        "trailing-newline",
        "bom",
        "truncated",
        "spaced",
        "key-order",
        "duplicate-key",
        "nan",
        "infinity",
        "float",
        "exponent",
        "escaped-unicode",
        "invalid-utf8",
        "binary",
    ],
)
def test_non_canonical_bytes_are_rejected_on_decode(payload: bytes) -> None:
    with pytest.raises(A2ContractError):
        A2HeaderCodec("zones", "1").decode(payload)


def test_byte_bounds_apply_on_both_paths() -> None:
    small = A2HeaderCodec("zones", "1", max_bytes=len(GOLDEN_ZONES) - 1)
    exact = A2HeaderCodec("zones", "1", max_bytes=len(GOLDEN_ZONES))
    with pytest.raises(A2ContractError):
        small.encode(envelope("zones", "1"))
    with pytest.raises(A2ContractError):
        small.decode(GOLDEN_ZONES)
    if exact.encode(envelope("zones", "1")) != GOLDEN_ZONES:
        pytest.fail("a payload at the exact bound must encode")
    if exact.decode(GOLDEN_ZONES) != envelope("zones", "1"):
        pytest.fail("a payload at the exact bound must decode")


def test_tampered_reference_or_bytes_are_rejected() -> None:
    registry = build_a2_semantic_registry()
    g = GOLDENS[-1]
    good, golden, count = g.ref, g.payload, len(g.payload)
    with pytest.raises(SemanticDataIntegrityError):
        registry.decode(dataclasses.replace(good, byte_count=count + 1), golden)
    with pytest.raises(SemanticDataIntegrityError):
        registry.decode(dataclasses.replace(good, sha256="0" * 64), golden)
    flipped = golden.replace(b'"n":1', b'"n":2')
    with pytest.raises(SemanticDataIntegrityError):
        registry.decode(good, flipped)
    with pytest.raises(SemanticDataReferenceError):
        registry.encode_for_reference(
            dataclasses.replace(good, sha256="1" * 64), envelope(g.kind, g.version)
        )


UNKNOWN_PAIRS = [
    ("zones", "2"),
    ("zones", "0"),
    ("prepared", "999"),
    ("a2_completion_receipt", "1"),
    ("unknown_kind", "1"),
    ("Zones", "1"),
    ("zones", "1 "),
    ("", ""),
]


@pytest.mark.parametrize(("kind", "version"), UNKNOWN_PAIRS)
def test_unknown_schema_is_rejected_everywhere(kind: str, version: str) -> None:
    semantic = build_a2_semantic_registry()
    results = build_a2_result_schema_registry()
    if results.supports(kind, version):
        pytest.fail("result registry accepted an unknown pair")
    with pytest.raises(A2UnknownSchemaError) as info:
        semantic.encode("d1", kind, version, {"header": header("zones", "1")})
    if not isinstance(info.value, UnknownSemanticDataSchemaError):
        pytest.fail("unknown schema must keep the persistence error type")
    if not kind or not version:
        return
    forged = SemanticDataRef("d1", kind, version, "0" * 64, 5)
    with pytest.raises(A2UnknownSchemaError):
        semantic.decode(forged, b"{}")


def test_unknown_schema_message_does_not_echo_input() -> None:
    with pytest.raises(A2UnknownSchemaError) as info:
        build_a2_semantic_registry().encode("d1", "secret_kind_9", "1", {})
    if "secret" in str(info.value):
        pytest.fail("error echoed caller input")


def test_old_result_registry_rows_are_unchanged() -> None:
    old = ResultSchemaRegistry.phase1()
    build_a2_result_schema_registry()
    build_a2_semantic_registry()
    if old.schemas != OLD_RESULT_PAIRS:
        pytest.fail("old result schema rows changed")
    if old.semantic_data_required != OLD_SEMANTIC_REQUIRED:
        pytest.fail("old semantic-data requirement rows changed")
    if ResultSchemaRegistry.phase1() != old:
        pytest.fail("old registry is not stable across calls")
    if not all(old.supports(k, v) for k, v in OLD_RESULT_PAIRS):
        pytest.fail("old registry lost a row")


def test_old_semantic_codec_rows_are_unchanged() -> None:
    build_a2_semantic_registry()
    old = SemanticDataRegistry.phase1()
    rows = [(c.kind, c.schema_version, c.max_bytes) for c in old._codecs]
    if rows != OLD_CODEC_ROWS:
        pytest.fail("old semantic codec rows changed")


@ALL
def test_old_registries_still_refuse_every_a2_pair(g: Golden) -> None:
    kind, version = g.kind, g.version
    old_results = ResultSchemaRegistry.phase1()
    old_semantic = SemanticDataRegistry.phase1()
    if old_results.supports(kind, version) or old_results.requires_data(kind, version):
        pytest.fail("old result registry accepted an A2 pair")
    with pytest.raises(UnknownSemanticDataSchemaError):
        old_semantic.encode("d1", kind, version, envelope(kind, version))
    with pytest.raises(UnknownSemanticDataSchemaError):
        old_semantic.decode(g.ref, g.payload)


@pytest.mark.parametrize(("kind", "version"), sorted(OLD_RESULT_PAIRS))
def test_a2_registry_refuses_every_old_row(kind: str, version: str) -> None:
    results = build_a2_result_schema_registry()
    if results.supports(kind, version):
        pytest.fail("A2 registry accepted an old row")
    with pytest.raises(A2RegistryError):
        results.require_supported(kind, version)
    with pytest.raises(A2UnknownSchemaError):
        build_a2_semantic_registry().encode("d1", kind, version, {})


def test_old_extension_path_is_unchanged() -> None:
    old = ResultSchemaRegistry.phase1()
    extended = old.with_schema("zones", "1", semantic_data_required=True)
    if extended.schemas != OLD_RESULT_PAIRS | {("zones", "1")}:
        pytest.fail("old with_schema result changed")
    if old.schemas != OLD_RESULT_PAIRS:
        pytest.fail("old with_schema mutated its source")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "defect: A2HeaderCodec.encode accepts a header without 'profile'. "
        "StageHeader defaults it, so the wire carries a profile-less header, "
        "a second byte form for one logical header."
    ),
)
def test_header_without_profile_is_rejected_on_encode() -> None:
    value = {"body": {"n": 1}, "header": {"kind": "zones", "version": "1"}}
    with pytest.raises(A2RegistryError):
        A2HeaderCodec("zones", "1").encode(value)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "defect: A2HeaderCodec.decode accepts canonical bytes whose header "
        "lacks 'profile'. Expected a rejection (A2ContractError family)."
    ),
)
def test_header_without_profile_is_rejected_on_decode() -> None:
    payload = b'{"body":{"n":1},"header":{"kind":"zones","version":"1"}}'
    with pytest.raises(A2ContractError):
        A2HeaderCodec("zones", "1").decode(payload)
