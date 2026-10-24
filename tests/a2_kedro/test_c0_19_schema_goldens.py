"""
C0-19 schema goldens for every accepted A2 v2 contract kind@version.

Provenance. Every SHA-256, field-name set, ID and limit below is a
hard-coded literal. The test never computes an expected value with the code
under test.

* Field-name sets and limits: reasoned from the decision record
  ``docs/decisions/a2-v2-schema-ids.md`` and the contract source.
* Frozen documents in ``golden_schema/c0_19_documents.json`` and their
  SHA-256 digests: the code was run ONCE on synthetic fixtures to print the
  canonical bytes. The output was reviewed for plausibility (sorted keys,
  no whitespace, synthetic ids, no address or subject text) and pasted in.
* The domain digest literal was computed with ``sha256sum``.

An intended wire change must update the fixture and the digest together.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import (
    MAX_CANONICAL_BYTES,
    MAX_DEPTH,
    MAX_TEXT_BYTES,
    A2ContractError,
    canonical_json_bytes,
    canonical_model_bytes,
    decode_canonical_json,
    decode_model_bytes,
    domain_sha256,
    sha256_hex,
)
from msgloom.a2_kedro.contracts.extract import ExtractedComponents
from msgloom.a2_kedro.contracts.header import approved_pairs
from msgloom.a2_kedro.contracts.held import InputDisposition
from msgloom.a2_kedro.contracts.parse import ParsedParts
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt
from msgloom.a2_kedro.contracts.relations import NativeRelations
from msgloom.a2_kedro.contracts.result_manifest import ResultManifest
from msgloom.a2_kedro.contracts.results import (
    FilterResult,
    GroupResult,
    Prepared,
    decode_result,
)
from msgloom.a2_kedro.contracts.schema_ids import (
    HISTORICAL_READ_ONLY,
    STAGE_SCHEMAS,
    require_stage_schema,
)
from msgloom.a2_kedro.contracts.source import FrozenSourceSelection
from msgloom.a2_kedro.contracts.transition import TransitionBatch
from msgloom.a2_kedro.contracts.zones import ContentZones, NormalizedContent
from tests.a2_kedro.helpers import check, stage_identity

FIXTURE = Path(__file__).parent / "golden_schema" / "c0_19_documents.json"

#: Kinds with their own codec outside ``contracts/`` (``triage_input@2``).
OTHER_CODEC = frozenset({"triage_input"})

#: kind@version -> (model, decoded attribute path, expected literal).
CASES: dict[str, tuple[Any, str, Any]] = {
    "frozen_source_selection@1": (FrozenSourceSelection, "incremental_roots.0.role", "primary"),
    "extracted_components@1": (ExtractedComponents, "components.0.reference", "saved/p"),
    "parsed_parts@1": (ParsedParts, "receipt.worker", "worker-1"),
    "normalized_content@1": (NormalizedContent, "parsed_length", 23),
    "zones@1": (ContentZones, "zones.1.kind", "quote"),
    "native_relations@1": (NativeRelations, "relations.0.kind", "reply_to"),
    "prepared@2": (Prepared, "sent_at", 1_700_000_000),
    "filter_result@2": (FilterResult, "verdict", "include"),
    "group_result@2": (GroupResult, "scope_id", "T1"),
    "prepared_transitions@2": (TransitionBatch, "items.0.kind", "context_refresh"),
    "a2_input_disposition@1": (InputDisposition, "repair_class", "operator_repair"),
    "a2_result_manifest@1": (ResultManifest, "policy_version", "policy-1"),
    "a2_completion_receipt@2": (CompletionReceipt, "roots.0.disposition", "prepared"),
}  # fmt: skip
MODELS: dict[str, Any] = {key: case[0] for key, case in CASES.items()}

#: SHA-256 of the exact canonical bytes of each frozen document.
GOLDEN_SHA: dict[str, str] = {
    "frozen_source_selection@1": "72cbe2018cba7cf2c17f05baf0c71c2db7c848bf6d52159a0ca80dea0c34690c",
    "extracted_components@1": "71954047baa93e3eebedc493790729f103bcc91076a4bdbc6eeb545d01cf90fe",
    "parsed_parts@1": "8e8f54bb5b10e27c4c5d8bc626e98d7e40b66607e3ff524b6c4beb17ba7c6bc6",
    "normalized_content@1": "967f48f53556daacec2f04aff5c9d4905bb06e0ed0736fcef3074eefc36fc049",
    "zones@1": "fed4f71dc317f0cbdb421d330fcaa37e1fd6acf882e588eece8ad2f08ea4ecd1",
    "native_relations@1": "cfd6ae7dcc175174cf9fefc7e8d1bfd6281f6063a975fe9b28ada83e31141a5c",
    "prepared@2": "ed7628f10554ce37434cfc3021a4852c864d40abafc656fe2df752207a187a07",
    "filter_result@2": "2cc402fb621f7dfb76d77f1d1497226cedf51313acd771b1a91bb1b699f3e699",
    "group_result@2": "e48cd167149f62619fc709de899cbe3fd3e284f019579671ca56e7536cda3538",
    "prepared_transitions@2": "ff6aced10bd9386379f281c90afbd72f000e7c48d29f25f2c33c3738a3790c13",
    "a2_input_disposition@1": "0df0b9dd2a0fb52f3458967f20e1b7ee76de323df4d457b7b0cff4c81f0f9f5c",
    "a2_result_manifest@1": "dcd7d1635e0d030b2b0bc211cd506bcf3e9453e515b35d923230ae69ed85534c",
    "a2_completion_receipt@2": "40145b70846454fc210d6f6a29867d6500e0044f79675e56d30928af0d8c37d4",
}  # fmt: skip

#: Exact top-level wire field names of each kind (space separated).
_WIRE = {
    "frozen_source_selection@1": "baseline_roots header incremental_roots scope selection_set_sha256 workset",
    "extracted_components@1": "components header",
    "parsed_parts@1": "cells header pages parts receipt sheets",
    "normalized_content@1": "header normalized_length normalized_sha256 parsed_length parsed_sha256 part_id segments",
    "zones@1": "header normalized_length normalized_sha256 parsed_length parsed_sha256 part_id zones",
    "native_relations@1": "header nodes relations",
    "prepared@2": "blocks header limitations lineage_sha256 normalized parsed participants parts relations root rule_version sent_at status zones",
    "filter_result@2": "evaluations header limitations matched policy_id policy_version prepared reasons status verdict",
    "group_result@2": "evidence header limitations members relations rule_version scope_id scope_kind status unknown",
    "prepared_transitions@2": "batch_sha256 code_version header items policy_version workset",
    "a2_input_disposition@1": "baseline_approval baseline_source code_version configuration_version entry reason repair_class selected selection_sha256 workset_index",
    "a2_result_manifest@1": "code_version configuration_version entries header limitations policy_version workset",
    "a2_completion_receipt@2": "acceptance_index_sha256 claim_proofs intake_held_count policy_version roots status transition_batch workset",
}  # fmt: skip


def names(text: str) -> frozenset[str]:
    return frozenset(text.split())


WIRE_FIELDS = {key: names(text) for key, text in _WIRE.items()}

#: (kind@version, path, exact field names) for nested records.
NESTED_FIELDS: list[tuple[str, tuple[str | int, ...], frozenset[str]]] = [
    ("prepared@2", ("header",), names("kind profile version")),
    (
        "prepared@2",
        ("root",),
        names(
            "a1_ordinal_proof baseline_approval baseline_source entry ordinal role "
            "selected selection_sha256 workset_index"
        ),
    ),
    (
        "prepared_transitions@2",
        ("items", 0),
        names("authority entry fact_id kind ordinal scope_id scope_kind"),
    ),
    (
        "a2_completion_receipt@2",
        ("roots", 0),
        names(
            "baseline_selection baseline_source disposition limitations result "
            "selection status workset_selection_index"
        ),
    ),
]

KEYS = sorted(MODELS)
HEADER_KEYS = [key for key in KEYS if "header" in WIRE_FIELDS[key]]
OMITTABLE = ("extracted_components@1", "a2_completion_receipt@2")
RESULT_NAMES = {"prepared", "filter_result", "group_result", "a2_result_manifest"}
RESULT_KEYS = [key for key in KEYS if key.partition("@")[0] in RESULT_NAMES]


def documents() -> dict[str, str]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def golden(key: str) -> bytes:
    return documents()[key].encode("utf-8")


def decode(key: str, data: bytes) -> Any:
    model = MODELS[key]
    if hasattr(model, "decode"):
        return model.decode(data)
    return decode_model_bytes(model, data)


def encode(key: str, value: Any) -> bytes:
    if hasattr(value, "encode"):
        return value.encode()
    return canonical_model_bytes(value)


def pretty(data: bytes) -> bytes:
    return json.dumps(json.loads(data), sort_keys=True).encode()


def reorder(data: bytes) -> bytes:
    value = json.loads(data)
    swapped = dict(reversed(list(value.items())))
    return json.dumps(swapped, separators=(",", ":"), ensure_ascii=False).encode()


def edit_doc(key: str, change: Any) -> bytes:
    """Return canonical bytes of the golden document after ``change``."""
    value = json.loads(golden(key))
    change(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def walk(value: Any, path: tuple[str | int, ...]) -> Any:
    for step in path:
        value = value[step]
    return value


def test_every_kind_has_one_literal_in_each_table() -> None:
    tables = (MODELS, GOLDEN_SHA, WIRE_FIELDS, documents())
    for table in tables:
        check(sorted(table) == KEYS, "table keys differ from the golden kinds")


@pytest.mark.parametrize("key", KEYS)
def test_canonical_bytes_hash_to_the_pinned_sha(key: str) -> None:
    data = golden(key)
    check(sha256_hex(data) == GOLDEN_SHA[key], key + ": golden bytes changed")
    check(decode_canonical_json(data) == json.loads(data), "canonical decode")


@pytest.mark.parametrize("key", KEYS)
def test_top_level_wire_field_names_are_pinned(key: str) -> None:
    check(set(json.loads(golden(key))) == WIRE_FIELDS[key], key + ": document")
    check(set(MODELS[key].model_fields) == WIRE_FIELDS[key], key + ": model")


@pytest.mark.parametrize(("key", "path", "names"), NESTED_FIELDS)
def test_nested_wire_field_names_are_pinned(
    key: str, path: tuple[str | int, ...], names: frozenset[str]
) -> None:
    check(set(walk(json.loads(golden(key)), path)) == names, key + str(path))


@pytest.mark.parametrize("key", HEADER_KEYS)
def test_header_names_the_kind_version_and_profile(key: str) -> None:
    kind, _, version = key.partition("@")
    header = json.loads(golden(key))["header"]
    check(
        header == {"kind": kind, "profile": "a2-c0-provisional-1", "version": version},
        key + ": header",
    )


def test_wire_limits_are_pinned() -> None:
    check(MAX_CANONICAL_BYTES == 4_194_304, "canonical byte bound")
    check(MAX_TEXT_BYTES == 2048, "text byte bound")
    check(MAX_DEPTH == 32, "depth bound")


def test_domain_digest_is_pinned() -> None:
    # sha256 of b'a2-test@1' + NUL + b'{"a":1,"b":[true,null,"x"]}'.
    value = {"b": [True, None, "x"], "a": 1}
    check(
        domain_sha256("a2-test@1", value)
        == "a35e12e5f8388363a513eaa45f86fa74423bb1ff8bd7560e88e1c131d2f05b6f",
        "domain digest changed",
    )
    check(
        domain_sha256("a2-test@2", value) != domain_sha256("a2-test@1", value),
        "domain separates digests",
    )


def test_logical_key_identity_is_pinned() -> None:
    check(
        stage_identity().logical_key()
        == "a2-accepted:40eca2e4dbbee7a1b677713e59dc56c41ed8244d58baedd720b4a8fd00743c7a",
        "stage logical key changed",
    )


@pytest.mark.parametrize("key", KEYS)
def test_frozen_document_decodes_and_re_encodes_to_identical_bytes(key: str) -> None:
    data = golden(key)
    value = decode(key, data)
    check(isinstance(value, MODELS[key]), key + ": model type")
    _, path, expected = CASES[key]
    actual: Any = value
    for step in path.split("."):
        actual = actual[int(step)] if step.isdigit() else getattr(actual, step)
    check(actual == expected, key + ": decoded value")
    check(encode(key, value) == data, key + ": re-encoded bytes differ")
    check(sha256_hex(encode(key, value)) == GOLDEN_SHA[key], key + ": sha")


@pytest.mark.parametrize("key", RESULT_KEYS)
def test_header_dispatch_decodes_the_frozen_result(key: str) -> None:
    value = decode_result(golden(key))
    check(type(value) is MODELS[key], key + ": dispatched type")


def defaulted_fields(key: str) -> list[str]:
    """Return optional fields whose frozen value equals their default."""
    value = decode(key, golden(key))
    fields = MODELS[key].model_fields.items()
    return sorted(
        name
        for name, field in fields
        if not field.is_required()
        and getattr(value, name) == field.get_default(call_default_factory=True)
    )


@pytest.mark.parametrize("key", KEYS)
def test_omitted_default_fields_decode_to_the_same_object(key: str) -> None:
    names = defaulted_fields(key)
    thin = edit_doc(key, lambda v: [v.pop(name, None) for name in names])
    value = decode(key, thin)
    check(value == decode(key, golden(key)), key + ": defaults differ")
    check(encode(key, value) == golden(key), key + ": defaults not re-encoded")
    check(bool(names) or key not in OMITTABLE, key + ": no omittable field")


@pytest.mark.parametrize("key", HEADER_KEYS)
@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("kind", "unknown_kind"),
        ("version", "99"),
        ("version", "0"),
        ("profile", "other-profile"),
    ],
)
def test_unknown_kind_version_or_profile_is_refused(
    key: str, field: str, bad: str
) -> None:
    data = edit_doc(key, lambda v: v["header"].__setitem__(field, bad))
    with pytest.raises(A2ContractError):
        decode(key, data)


@pytest.mark.parametrize("key", RESULT_KEYS)
def test_dispatch_refuses_unknown_pair_and_historical_pair(key: str) -> None:
    kind = key.partition("@")[0]
    unknown = edit_doc(key, lambda v: v["header"].__setitem__("kind", "nope"))
    with pytest.raises(A2ContractError):
        decode_result(unknown)
    wrong = edit_doc(key, lambda v: v["header"].__setitem__("version", "7"))
    with pytest.raises(A2ContractError):
        decode_result(wrong)
    if (kind, "1") in HISTORICAL_READ_ONLY:
        old = edit_doc(key, lambda v: v["header"].__setitem__("version", "1"))
        with pytest.raises(A2ContractError, match="historical"):
            decode_result(old)
    with pytest.raises(A2ContractError):
        decode_result(b"{}")


def test_historical_pairs_are_read_only_and_unknown_pairs_refused() -> None:
    check(
        HISTORICAL_READ_ONLY
        == frozenset(
            {("prepared", "1"), ("filter_result", "1"), ("group_result", "1")}
        ),
        "historical set changed",
    )
    for kind, version in sorted(HISTORICAL_READ_ONLY):
        with pytest.raises(A2ContractError, match="read-only"):
            require_stage_schema(kind, version)
    for kind, version in (("prepared", "3"), ("nope", "1"), ("zones", "2")):
        with pytest.raises(A2ContractError, match="not approved"):
            require_stage_schema(kind, version)


def required_fields(key: str) -> list[str]:
    fields = MODELS[key].model_fields.items()
    return sorted(name for name, field in fields if field.is_required())


@pytest.mark.parametrize("key", KEYS)
def test_each_missing_required_field_is_refused(key: str) -> None:
    names = required_fields(key)
    check(bool(names), key + ": no required field")
    for name in names:
        data = edit_doc(key, lambda v, n=name: v.pop(n))
        with pytest.raises(A2ContractError):
            decode(key, data)


@pytest.mark.parametrize("key", KEYS)
def test_extra_field_is_refused(key: str) -> None:
    data = edit_doc(key, lambda v: v.__setitem__("zz_extra", "x"))
    with pytest.raises(A2ContractError):
        decode(key, data)


@pytest.mark.parametrize("key", KEYS)
def test_non_canonical_key_order_and_whitespace_are_refused(key: str) -> None:
    good = golden(key)
    variants = {
        "reordered": reorder(good),
        "spaced": pretty(good),
        "newline": good + b"\n",
        "bom": b"\xef\xbb\xbf" + good,
        "escaped": b'{"' + b"\\u%04x" % good[2] + good[3:],
    }
    for name, data in variants.items():
        check(data != good, name + ": variant equals the golden")
        with pytest.raises(A2ContractError):
            decode(key, data)


@pytest.mark.parametrize("key", KEYS)
def test_duplicate_json_keys_are_refused(key: str) -> None:
    text = golden(key).decode()
    first = text[2 : text.index('"', 2)]
    data = ('{"' + first + '":null,' + text[1:]).encode()
    with pytest.raises(A2ContractError, match="duplicate"):
        decode(key, data)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("key", KEYS)
def test_non_finite_numbers_are_refused(key: str, constant: str) -> None:
    text = golden(key).decode()
    data = ('{"zz":' + constant + "," + text[1:]).encode()
    with pytest.raises(A2ContractError, match="non-finite"):
        decode(key, data)


def test_float_and_non_json_values_are_refused() -> None:
    with pytest.raises(A2ContractError):
        decode_canonical_json(b'{"a":1.5}')
    with pytest.raises(A2ContractError):
        decode_canonical_json(b'{"a":1e2}')
    for bad in (float("nan"), float("inf"), 1.5, {1: "x"}, {"a": {"b": {1, 2}}}):
        with pytest.raises(A2ContractError):
            canonical_json_bytes(bad)
    deep: Any = "x"
    for _ in range(MAX_DEPTH + 1):
        deep = [deep]
    with pytest.raises(A2ContractError):
        canonical_json_bytes(deep)


@pytest.mark.parametrize("key", KEYS)
def test_input_over_the_byte_bound_is_refused(key: str) -> None:
    data = golden(key)
    model = MODELS[key]
    check(decode_model_bytes(model, data, max_bytes=len(data)) is not None, "at bound")
    with pytest.raises(A2ContractError):
        decode_model_bytes(model, data, max_bytes=len(data) - 1)
    with pytest.raises(A2ContractError):
        decode_canonical_json(data, max_bytes=len(data) - 1)
    with pytest.raises(A2ContractError):
        canonical_json_bytes(json.loads(data), max_bytes=len(data) - 1)
    with pytest.raises(A2ContractError):
        decode(key, b" " * (MAX_CANONICAL_BYTES + 1))


def test_text_over_the_text_bound_is_refused() -> None:
    key = "extracted_components@1"
    data = edit_doc(
        key, lambda v: v["components"][0].__setitem__("reference", "x" * 2049)
    )
    with pytest.raises(A2ContractError):
        decode(key, data)
    fits = edit_doc(
        key, lambda v: v["components"][0].__setitem__("reference", "x" * 2048)
    )
    check(decode(key, fits).components[0].reference == "x" * 2048, "text at bound")


@pytest.mark.parametrize("key", KEYS)
def test_invalid_bytes_are_refused(key: str) -> None:
    for data in (b"", b"\xff\xfe", b"[]", b"null", b'{"header":'):
        with pytest.raises(A2ContractError):
            decode(key, data)


def test_every_registered_kind_has_a_golden() -> None:
    registry = {f"{kind}@{ver}" for kind, ver in approved_pairs().items()}
    covered = set(KEYS) | {
        f"{kind}@{ver}" for kind, ver in approved_pairs().items() if kind in OTHER_CODEC
    }
    missing = sorted(registry - covered)
    check(not missing, "registered without a C0-19 golden: " + ", ".join(missing))
    stale = sorted(set(KEYS) - registry)
    check(not stale, "golden for an unregistered kind: " + ", ".join(stale))


def test_golden_versions_match_the_registry() -> None:
    pairs = approved_pairs()
    for key in KEYS:
        kind, _, version = key.partition("@")
        check(pairs.get(kind) == version, key + ": version differs from registry")
    check(set(STAGE_SCHEMAS) <= set(pairs), "stage kinds are registered")
    uncovered = sorted(set(pairs) - {k.partition("@")[0] for k in KEYS})
    check(uncovered == sorted(OTHER_CODEC), "only triage_input is outside C0-19")
