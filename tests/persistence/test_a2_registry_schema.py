"""Closed A2 v2 registry factory tests (C0-21a); no database, no network."""

from __future__ import annotations

import dataclasses
import hashlib
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.header import StageHeader, approved_pairs
from msgloom.a2_kedro.contracts.schema_ids import HISTORICAL_READ_ONLY
from msgloom.contracts import ResultSchemaRegistry
from msgloom.persistence.a2_registry import (
    A2_APPROVED_PAIRS,
    A2HeaderCodec,
    A2RegistryError,
    A2ResultSchemaRegistry,
    A2SemanticDataRegistry,
    A2UnknownSchemaError,
    build_a2_result_schema_registry,
    build_a2_semantic_registry,
    parse_a2_pair,
    require_a2_pair,
)
from msgloom.persistence.errors import (
    SemanticDataIntegrityError,
    SemanticDataTypeError,
    UnknownSemanticDataSchemaError,
)
from msgloom.persistence.semantic import SemanticDataRegistry

APPROVED = sorted(approved_pairs().items())
OLD_RESULT_PAIRS = sorted(ResultSchemaRegistry.phase1().schemas)
BAD_VERSIONS = ["0", "3", "999", "", "1 ", " 1", "01x", "２", "v2"]


def payload(kind: str, version: str) -> dict[str, Any]:
    header = StageHeader(kind=kind, version=version).model_dump(mode="json")
    return {"header": header, "body": {"n": 1}}


def old_snapshot() -> tuple[object, ...]:
    result = ResultSchemaRegistry.phase1()
    semantic = SemanticDataRegistry.phase1()
    return (
        result.schemas,
        result.semantic_data_required,
        tuple((c.kind, c.schema_version, c.max_bytes) for c in semantic._codecs),
    )


LITERAL_APPROVED_PAIRS = frozenset(
    {
        ("a2_completion_receipt", "2"),
        ("a2_input_disposition", "1"),
        ("a2_result_manifest", "1"),
        ("extracted_components", "1"),
        ("filter_result", "2"),
        ("frozen_source_selection", "1"),
        ("group_result", "2"),
        ("native_relations", "1"),
        ("normalized_content", "1"),
        ("parsed_parts", "1"),
        ("prepared", "2"),
        ("prepared_transitions", "2"),
        ("triage_input", "2"),
        ("zones", "1"),
    }
)


def test_allowlist_is_derived_frozen_and_complete() -> None:
    if not isinstance(A2_APPROVED_PAIRS, frozenset):
        pytest.fail("allowlist must be a frozenset")
    if A2_APPROVED_PAIRS != frozenset(approved_pairs().items()):
        pytest.fail("allowlist differs from approved_pairs()")
    if len(A2_APPROVED_PAIRS) != 14:
        pytest.fail("expected 12 stage pairs and 2 external pairs")
    if A2_APPROVED_PAIRS != LITERAL_APPROVED_PAIRS:
        pytest.fail("allowlist differs from the pinned literal pair set")


@pytest.mark.parametrize(("kind", "version"), APPROVED)
def test_every_approved_pair_resolves(kind: str, version: str) -> None:
    results = build_a2_result_schema_registry()
    semantic = build_a2_semantic_registry()
    if not results.supports(kind, version):
        pytest.fail("result registry refused an approved pair")
    if not results.requires_data(kind, version):
        pytest.fail("approved pair must require semantic data")
    if require_a2_pair(kind, version) != (kind, version):
        pytest.fail("require_a2_pair changed the pair")
    if parse_a2_pair(f"{kind}@{version}") != (kind, version):
        pytest.fail("parse_a2_pair changed the pair")
    results.require_supported(kind, version)
    value = payload(kind, version)
    encoded = semantic.encode("d1", kind, version, value)
    if semantic.decode(encoded.reference, encoded.payload) != value:
        pytest.fail("round trip changed the payload")


def test_registry_holds_exactly_the_allowlist() -> None:
    results = build_a2_result_schema_registry()
    semantic = build_a2_semantic_registry()
    if results.schemas != A2_APPROVED_PAIRS:
        pytest.fail("result registry pair set differs")
    if results.semantic_data_required != A2_APPROVED_PAIRS:
        pytest.fail("semantic requirement set differs")
    if semantic.pairs != A2_APPROVED_PAIRS:
        pytest.fail("semantic registry pair set differs")


def other_pairs() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    kinds = {k for k, _ in APPROVED} | {k for k, _ in OLD_RESULT_PAIRS}
    for kind in sorted(kinds):
        for version in ("1", "2", "3", "999"):
            if (kind, version) not in A2_APPROVED_PAIRS:
                pairs.append((kind, version))
    return pairs


@pytest.mark.parametrize(("kind", "version"), other_pairs())
def test_every_other_pair_is_rejected(kind: str, version: str) -> None:
    results = build_a2_result_schema_registry()
    semantic = build_a2_semantic_registry()
    if results.supports(kind, version) or results.requires_data(kind, version):
        pytest.fail("result registry accepted a pair outside the allowlist")
    with pytest.raises(A2RegistryError):
        results.require_supported(kind, version)
    with pytest.raises(A2RegistryError):
        require_a2_pair(kind, version)
    with pytest.raises(A2RegistryError):
        parse_a2_pair(f"{kind}@{version}")
    with pytest.raises(A2UnknownSchemaError):
        semantic.encode("d1", kind, version, {"header": {}})


def test_other_pairs_cover_historical_old_kinds_and_next_version() -> None:
    covered = set(other_pairs())
    for pair in HISTORICAL_READ_ONLY:
        if pair not in covered:
            pytest.fail("historical pair is not covered")
    if ("triage_input", "1") not in covered or ("prepared", "999") not in covered:
        pytest.fail("old kind or next version is not covered")
    if ("collected_selection", "1") not in covered:
        pytest.fail("Phase 1 only kind is not covered")


@pytest.mark.parametrize("version", BAD_VERSIONS)
def test_wrong_or_malformed_version_is_rejected(version: str) -> None:
    with pytest.raises(A2RegistryError):
        require_a2_pair("prepared", version)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "prepared",
        "prepared@",
        "@2",
        "prepared@2@2",
        "prepared@2\n",
        " prepared@2",
        "prepared @2",
        "prepared@ 2",
        "Prepared@2",
        "prepared@２",
        "prepared:2",
        "prepared@2\x00",
        "prépared@2",
        "unknown_kind@1",
        "prepared@1",
        "prepared@999",
    ],
)
def test_malformed_or_unapproved_text_is_rejected(text: str) -> None:
    with pytest.raises(A2RegistryError):
        parse_a2_pair(text)


@pytest.mark.parametrize("value", [None, 2, b"prepared", ["prepared", "2"]])
def test_non_text_is_rejected(value: object) -> None:
    with pytest.raises(A2RegistryError):
        parse_a2_pair(value)
    with pytest.raises(A2RegistryError):
        require_a2_pair(value, "2")
    with pytest.raises(A2RegistryError):
        require_a2_pair("prepared", value)


def test_errors_belong_to_the_contract_family() -> None:
    if not issubclass(A2RegistryError, A2ContractError):
        pytest.fail("A2RegistryError must extend A2ContractError")
    if not issubclass(A2UnknownSchemaError, UnknownSemanticDataSchemaError):
        pytest.fail("unknown semantic lookup must keep the persistence error")


def test_error_messages_do_not_echo_input() -> None:
    secret = "secret-kind-7c1f@1"
    with pytest.raises(A2RegistryError) as info:
        parse_a2_pair(secret)
    if "secret" in str(info.value):
        pytest.fail("error echoed caller input")


def test_duplicate_registration_is_rejected() -> None:
    pairs = list(APPROVED)
    with pytest.raises(A2RegistryError, match="duplicate"):
        A2ResultSchemaRegistry.from_pairs([*pairs, pairs[0]])
    codecs = tuple(A2HeaderCodec(k, v) for k, v in pairs)
    with pytest.raises(A2RegistryError, match="duplicate"):
        A2SemanticDataRegistry((*codecs, codecs[0]))


def test_partial_or_extended_registration_is_rejected() -> None:
    with pytest.raises(A2RegistryError):
        A2ResultSchemaRegistry.from_pairs(APPROVED[:-1])
    with pytest.raises(A2RegistryError):
        A2ResultSchemaRegistry.from_pairs([*APPROVED, ("triage", "1")])
    with pytest.raises(A2RegistryError):
        A2SemanticDataRegistry(tuple(A2HeaderCodec(k, v) for k, v in APPROVED[:-1]))
    with pytest.raises(A2RegistryError):
        A2HeaderCodec("prepared", "1")


def test_direct_construction_cannot_widen_or_weaken() -> None:
    with pytest.raises(A2RegistryError):
        A2ResultSchemaRegistry(A2_APPROVED_PAIRS | {("triage", "1")})
    with pytest.raises(A2RegistryError):
        A2ResultSchemaRegistry(A2_APPROVED_PAIRS)
    with pytest.raises(A2RegistryError):
        A2ResultSchemaRegistry(frozenset(), frozenset())


def test_result_registry_cannot_be_extended_or_mutated() -> None:
    registry = build_a2_result_schema_registry()
    with pytest.raises(A2RegistryError):
        registry.with_schema("triage", "1")
    with pytest.raises(A2RegistryError):
        registry.with_schema("prepared", "2", semantic_data_required=True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        registry.schemas = frozenset()  # type: ignore[misc]
    if registry.schemas != A2_APPROVED_PAIRS:
        pytest.fail("registry changed after refused extension")


def test_semantic_registry_is_sealed() -> None:
    registry = build_a2_semantic_registry()
    with pytest.raises(A2RegistryError):
        registry._codecs = ()
    with pytest.raises(A2RegistryError):
        registry.extra = 1  # type: ignore[attr-defined]
    with pytest.raises(A2RegistryError):
        del registry._codecs
    if registry.pairs != A2_APPROVED_PAIRS:
        pytest.fail("registry changed after refused writes")


def test_calls_return_independent_registries() -> None:
    first, second = build_a2_result_schema_registry(), build_a2_result_schema_registry()
    if first is second:
        pytest.fail("result factory returned a shared object")
    one, two = build_a2_semantic_registry(), build_a2_semantic_registry()
    if one is two or one._codecs is two._codecs:
        pytest.fail("semantic factory shared state")
    with pytest.raises(A2RegistryError):
        one._codecs = ()
    if two.pairs != A2_APPROVED_PAIRS or one.pairs != A2_APPROVED_PAIRS:
        pytest.fail("a refused mutation reached another registry")


def test_old_phase1_registries_are_unchanged_and_separate() -> None:
    before = old_snapshot()
    results = build_a2_result_schema_registry()
    semantic = build_a2_semantic_registry()
    if old_snapshot() != before:
        pytest.fail("phase1() behavior changed after the A2 factory ran")
    old_results, old_semantic = (
        ResultSchemaRegistry.phase1(),
        SemanticDataRegistry.phase1(),
    )
    if results is old_results or semantic is old_semantic:
        pytest.fail("A2 registry must be a different object")
    if type(old_results) is not ResultSchemaRegistry:
        pytest.fail("old registry class changed")
    if type(old_semantic) is not SemanticDataRegistry:
        pytest.fail("old semantic class changed")
    if results == old_results:
        pytest.fail("A2 registry must not equal the Phase 1 registry")
    if old_results.supports("prepared", "2") or old_results.supports("zones", "1"):
        pytest.fail("Phase 1 registry accepted an A2 pair")
    with pytest.raises(UnknownSemanticDataSchemaError):
        old_semantic.encode("d1", "zones", "1", {})
    if {"prepared@1", "triage_input@1"} - {f"{k}@{v}" for k, v in old_snapshot()[0]}:  # type: ignore[attr-defined]
        pytest.fail("Phase 1 snapshot lost a kind")


def test_phase1_extension_path_is_untouched() -> None:
    extended = ResultSchemaRegistry.phase1().with_schema("zones", "1")
    if not extended.supports("zones", "1"):
        pytest.fail("old with_schema behavior changed")
    if isinstance(extended, A2ResultSchemaRegistry):
        pytest.fail("old registry produced an A2 registry")
    if not isinstance(build_a2_semantic_registry(), SemanticDataRegistry):
        pytest.fail("A2 semantic registry must stay store compatible")


def test_codec_checks_header_pair_and_shape() -> None:
    registry = build_a2_semantic_registry()
    with pytest.raises(A2RegistryError):
        registry.encode("d1", "prepared", "2", payload("filter_result", "2"))
    with pytest.raises(A2RegistryError):
        registry.encode("d1", "prepared", "2", {"body": {}})
    old = {"header": {"kind": "prepared", "version": "1"}, "body": {}}
    with pytest.raises(A2RegistryError):
        registry.encode("d1", "prepared", "2", old)
    with pytest.raises(SemanticDataTypeError):
        registry.encode("d1", "prepared", "2", "text")


def test_decode_rejects_tampered_and_non_canonical_bytes() -> None:
    registry = build_a2_semantic_registry()
    encoded = registry.encode("d1", "zones", "1", payload("zones", "1"))
    with pytest.raises(SemanticDataIntegrityError):
        registry.decode(encoded.reference, encoded.payload + b" ")
    spaced = encoded.payload.replace(b",", b", ")
    other = dataclasses.replace(
        encoded.reference,
        sha256=hashlib.sha256(spaced).hexdigest(),
        byte_count=len(spaced),
    )
    with pytest.raises(SemanticDataIntegrityError):
        registry.decode(other, spaced)


def test_codec_decode_wraps_deep_nesting() -> None:
    codec = A2HeaderCodec("zones", "1")
    deep = b"[" * 100_000 + b"]" * 100_000
    with pytest.raises((A2RegistryError, A2ContractError)):
        codec.decode(deep)
