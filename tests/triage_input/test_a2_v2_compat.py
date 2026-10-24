"""C0-17d: v1 and v2 triage input compatibility. Synthetic data only.

Every expected digest, count and role below is a hand-pinned literal. The
v1 goldens come from ``build_triage_input`` on synthetic records. The v2
goldens come from the C0-17a fixture. Both readers go through the C0-17c
adapter, so one test body checks both versions.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import canonical_json_bytes
from msgloom.contracts import ResultRef
from msgloom.triage_input import (
    SourceRole,
    TriageInputCodec,
    TriageInputSnapshot,
    build_triage_input,
)
from msgloom.triage_input import adapter_v2 as adapter
from msgloom.triage_input.adapter_v2 import (
    AdapterError,
    InputTooLargeError,
    LossyProjectionError,
    MixedVersionsError,
    UnsupportedVersionError,
    V1ReadError,
    classify_upstream,
    project_to_v1,
    read_triage_input,
    summarize_v2,
)
from msgloom.triage_input.codec_v2 import (
    DigestMismatchError,
    HistoricalVersionError,
    OversizedInputError,
    SchemaViolationError,
    TriageInputV2Codec,
    TriageInputV2Error,
    UnknownKindError,
    UnknownVersionError,
    seal_snapshot,
)
from tests.a2_kedro.helpers import check
from tests.a2_kedro.test_c0_17a import edit, incomplete_data, load, snapshot_data
from tests.triage_input.helpers import config, exclusion_filter, record, selection

V2CODEC = TriageInputV2Codec()
ZERO = "0" * 64

#: Pinned v1 goldens: (snapshot, selection-binding, configuration) hashes.
V1_GOLDENS: dict[str, tuple[str, str, str]] = {
    "pair": (
        "3b8534f7f82705a0dffe52da417846392d85a5cb2dd46467caac7c5ee263befb",
        "6a8a9322613f419cbfe766caf26d1bee76b472f2398c3f561cae5227ed8c8c95",
        "0b8f0a7a94879bce7fe1eadf16c694dad0aa0de45655c9a2f0caf1a8ac077d16",
    ),
    "held": (
        "a93fdf0046abed7886df7251e686ab328075e9bdb86c6969911ede6bb475f47e",
        "a20b101f3c277d1a198db2f3c6f1e94896adf08d1a2694d4b03f5d4123ee4acf",
        "0b8f0a7a94879bce7fe1eadf16c694dad0aa0de45655c9a2f0caf1a8ac077d16",
    ),
    "partial": (
        "62c09296e638744c4fb62f332a734005f0719516227df170a91d92e6574fd913",
        "dc7d35a015ba1d518a95e5bfea8fa7f8a917041425acd09e6660379cbeb7864d",
        "521618006ec39e90dc54ce8eea0778d32f7b73fef9babb50706763ec48133961",
    ),
}
#: Pinned v2 goldens: (binding, configuration, snapshot) digests, byte size.
V2_GOLDENS: dict[str, tuple[str, str, str, int]] = {
    "complete": (
        "21407dce84e36e04ed8aae37f8edb9855a3e1b8e8ea64974bb33987375d56c34",
        "5f734b914982bc85b044fd4a6ed1079e7b5a49f3c2b039d33df553b78b9c8f30",
        "f2d1417e4b7825821260644f06ef553e29c5ac165d9f0b34c40bf48a7c6a99e4",
        6143,
    ),
    "incomplete": (
        "21407dce84e36e04ed8aae37f8edb9855a3e1b8e8ea64974bb33987375d56c34",
        "5f734b914982bc85b044fd4a6ed1079e7b5a49f3c2b039d33df553b78b9c8f30",
        "fe6ccd383fbdfaf4c53d8e857d25e275ec1951dbfda57239df9475e0edec76c4",
        6456,
    ),
}
A_ID = "a2-accepted:" + "a" * 64
B_ID = "a2-accepted:" + "b" * 64
C_ID = "a2-accepted:" + "c" * 64


@cache
def v1_snapshot(name: str) -> TriageInputSnapshot:
    """Build one deterministic v1 snapshot. Cached: the builds are slow."""
    if name == "pair":
        roles = (SourceRole.EARLIER_CONTEXT, SourceRole.NEW_SOURCE)
        chosen = selection((record("old"), record("new")), roles=roles)
        return build_triage_input(chosen, config())
    if name == "held":
        chosen = selection((record("held"),), filter_config=exclusion_filter("held"))
        return build_triage_input(chosen, config())
    chosen = selection((record("too-large", body="word " * 3000),))
    return build_triage_input(chosen, config(max_part_bytes=1500, max_parts=2))


def v1_bytes(name: str) -> bytes:
    return TriageInputCodec().encode(v1_snapshot(name))


def v2_bytes(name: str) -> bytes:
    return V2CODEC.encode(seal_snapshot(load(V2_DATA[name]())))


V2_DATA = {"complete": snapshot_data, "incomplete": incomplete_data}


def dump(data: dict[str, Any]) -> bytes:
    """Return canonical bytes of ``data`` with no validation or resealing."""
    return canonical_json_bytes(data, max_bytes=2**31)


def tampered_v1(name: str, path: str, value: Any) -> bytes:
    return dump(edit(json.loads(v1_bytes(name)), path, value))


def tampered_v2(name: str, path: str, value: Any) -> bytes:
    return dump(edit(json.loads(v2_bytes(name)), path, value))


def refuses(payload: bytes, error: type[Exception]) -> Exception:
    """Check ``read_triage_input`` raises exactly ``error`` with no chain."""
    with pytest.raises(error) as caught:
        read_triage_input(payload)
    found = caught.value
    check(type(found) is error, f"expected {error.__name__}, got {type(found)}")
    check(found.__cause__ is None, "no chained cause")
    check(found.__context__ is None, "no chained context")
    return found


# -- positive: goldens of both versions load ------------------------------------


@pytest.mark.parametrize("name", ["pair", "held", "partial"])
def test_historical_v1_goldens_load_with_pinned_hashes(
    name: str, tmp_path: Path
) -> None:
    path = tmp_path / "v1.json"
    path.write_bytes(v1_bytes(name))
    result = read_triage_input(path.read_bytes())
    check(result.version == "1", "v1 reader owns v1 bytes")
    value = result.value
    check(isinstance(value, TriageInputSnapshot), "v1 snapshot type")
    snapshot, selected, config_hash = V1_GOLDENS[name]
    check(value.snapshot_hash == snapshot, "snapshot hash")  # type: ignore[union-attr]
    check(value.selection_binding_hash == selected, "binding hash")  # type: ignore[union-attr]
    check(value.configuration_hash == config_hash, "configuration hash")  # type: ignore[union-attr]
    check(TriageInputCodec().encode(value) == path.read_bytes(), "byte stable")  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["complete", "incomplete"])
def test_new_v2_goldens_load_with_pinned_digests(name: str, tmp_path: Path) -> None:
    path = tmp_path / "v2.json"
    path.write_bytes(v2_bytes(name))
    binding, configuration, snapshot, size = V2_GOLDENS[name]
    check(len(path.read_bytes()) == size, "payload size")
    result = read_triage_input(path.read_bytes())
    check(result.version == "2", "v2 reader owns v2 bytes")
    value = result.value
    check(value.binding_sha256 == binding, "binding digest")  # type: ignore[union-attr]
    check(value.configuration_sha256 == configuration, "configuration digest")  # type: ignore[union-attr]
    check(value.snapshot_sha256 == snapshot, "snapshot digest")  # type: ignore[union-attr]
    check(V2CODEC.encode(value) == path.read_bytes(), "byte stable")  # type: ignore[arg-type]


def test_both_versions_load_in_one_process_without_cross_effect() -> None:
    first = read_triage_input(v1_bytes("pair"))
    second = read_triage_input(v2_bytes("complete"))
    third = read_triage_input(v1_bytes("pair"))
    check((first.version, second.version) == ("1", "2"), "versions")
    check(first == third, "v1 result is unchanged by a v2 read")
    check(v1_bytes("pair") == TriageInputCodec().encode(first.value), "v1 bytes")  # type: ignore[arg-type]


# -- consistent digest, parts and selected roles ---------------------------------


def test_v1_and_v2_expose_digests_parts_and_roles_consistently() -> None:
    old = read_triage_input(v1_bytes("pair")).value
    new = read_triage_input(v2_bytes("complete")).value
    hashes = (old.snapshot_hash, old.selection_binding_hash, old.configuration_hash)  # type: ignore[union-attr]
    digests = (new.snapshot_sha256, new.binding_sha256, new.configuration_sha256)  # type: ignore[union-attr]
    for group in (hashes, digests):
        for item in group:
            check(len(item) == 64, "64 hex characters")
            check(item == item.lower() and int(item, 16) >= 0, "lowercase hex")
        check(len(set(group)) == 3, "three different digests")
    # v1: two active units, 45 parts. v2 fixture: one unit, two parts.
    check((len(old.units), len(old.parts)) == (2, 45), "v1 parts")  # type: ignore[union-attr]
    check((len(new.units), len(new.parts)) == (1, 2), "v2 parts")  # type: ignore[union-attr]
    check({str(p.state) for p in old.parts} == {"pending"}, "v1 parts pending")  # type: ignore[union-attr]
    check({str(p.state) for p in new.parts} == {"pending"}, "v2 parts pending")  # type: ignore[union-attr]
    v1_roles = [(r.source_ref.identity, str(r.role)) for r in old.selected_sources]  # type: ignore[union-attr]
    v2_roles = [(r.prepared.result_id, str(r.role)) for r in new.binding.roles]  # type: ignore[union-attr]
    check(
        v1_roles == [("new", "new-source"), ("old", "earlier-context")],
        f"v1 roles sorted by source {v1_roles}",
    )
    check(
        v2_roles
        == [
            (A_ID, "new-source"),
            (B_ID, "baseline-context"),
            (C_ID, "earlier-context"),
        ],
        f"v2 roles sorted by key {v2_roles}",
    )


def test_baseline_context_exists_only_in_v2() -> None:
    check({str(r) for r in SourceRole} == {"earlier-context", "new-source"}, "v1")
    bad = tampered_v1("pair", "selected_sources.0.role", "baseline-context")
    refuses(bad, V1ReadError)
    check("baseline-context" in v2_bytes("complete").decode(), "v2 keeps the role")


# -- partial and held state is never lost ---------------------------------------


def test_v1_partial_and_held_survive_the_adapter() -> None:
    partial = read_triage_input(v1_bytes("partial")).value
    check(partial.complete is False, "partial stays incomplete")  # type: ignore[union-attr]
    check(len(partial.parts) == 2, "retained parts kept")  # type: ignore[union-attr]
    failure = v1_snapshot("partial").failures[0]
    check(partial.failures == (failure,), "adapter keeps the build failure")  # type: ignore[union-attr]
    check(failure.reason == "part-count-exceeded", "failure reason")
    check((failure.first_occurrence, failure.remaining_occurrences) == (4, 185), "span")
    check(
        failure.remaining_digest
        == "ef418298f5470149a4ede70f6d3f6a86e1676c28a99284d9582f633516726c7f",
        "remaining digest",
    )
    held = read_triage_input(v1_bytes("held")).value
    check(len(held.held) == 1 and not held.parts, "held kept, nothing sent")  # type: ignore[union-attr]
    check(str(held.held[0].reasons[0]) == "filter-excluded", "held reason")  # type: ignore[union-attr]
    check(held.held[0].source_ref.identity == "held", "held source")  # type: ignore[union-attr]


def test_v2_partial_and_held_survive_the_adapter() -> None:
    summary = summarize_v2(read_triage_input(v2_bytes("incomplete")).value)  # type: ignore[arg-type]
    check(summary.complete is False, "incomplete")
    check(summary.held_sources == 1, "held kept")
    check(summary.coverage_failures == 1, "failure kept")
    check(summary.pending_parts == 2, "parts kept")
    check(summary.selected_sources == 3, "roles kept")
    check(
        [(x.code, x.detail) for x in summary.limitations]
        == [("coverage_incomplete", "unit")],
        "limitation",
    )
    whole = summarize_v2(read_triage_input(v2_bytes("complete")).value)  # type: ignore[arg-type]
    check(whole.complete and not whole.limitations, "complete has no limitation")
    check((whole.held_sources, whole.coverage_failures) == (1, 0), "held but whole")


@pytest.mark.parametrize(
    ("name", "reasons"),
    [
        ("complete", ("v2-references", "held-sources", "baseline-context-role")),
        (
            "incomplete",
            (
                "v2-references",
                "limitations",
                "held-sources",
                "coverage-failures",
                "incomplete-state",
                "baseline-context-role",
            ),
        ),
    ],
)
def test_v2_to_v1_projection_is_refused_with_every_reason(
    name: str, reasons: tuple[str, ...]
) -> None:
    value = read_triage_input(v2_bytes(name)).value
    with pytest.raises(LossyProjectionError) as caught:
        project_to_v1(value)  # type: ignore[arg-type]
    check(caught.value.reasons == reasons, f"reasons {caught.value.reasons}")


@pytest.mark.parametrize(
    ("version", "name", "path", "value"),
    [
        ("1", "partial", "failures", []),
        ("1", "partial", "complete", True),
        ("1", "held", "held", []),
        ("1", "held", "selected_sources", []),
        ("2", "incomplete", "failures", []),
        ("2", "incomplete", "limitations", []),
        ("2", "incomplete", "complete", True),
        ("2", "complete", "held", []),
        ("2", "complete", "units", []),
        ("2", "complete", "binding.roles", []),
    ],
)
def test_dropping_partial_or_held_state_is_rejected(
    version: str, name: str, path: str, value: Any
) -> None:
    if version == "1":
        refuses(tampered_v1(name, path, value), V1ReadError)
        return
    refuses(tampered_v2(name, path, value), SchemaViolationError)


# -- negative: tampered digest ---------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["snapshot_hash", "selection_binding_hash", "configuration_hash", "selection_hash"],
)
def test_v1_tampered_digest_is_rejected(path: str) -> None:
    refuses(tampered_v1("pair", path, ZERO), V1ReadError)


@pytest.mark.parametrize(
    "path", ["snapshot_sha256", "binding_sha256", "configuration_sha256"]
)
def test_v2_tampered_digest_is_rejected(path: str) -> None:
    refuses(tampered_v2("complete", path, ZERO), DigestMismatchError)


def test_changed_selected_role_without_resealing_is_rejected() -> None:
    refuses(
        tampered_v1("pair", "selected_sources.0.role", "earlier-context"), V1ReadError
    )
    refuses(
        tampered_v2("complete", "binding.roles.0.role", "earlier-context"),
        DigestMismatchError,
    )


# -- negative: missing roles -----------------------------------------------------


def test_v2_missing_or_unknown_role_is_rejected() -> None:
    data = json.loads(v2_bytes("complete"))
    one_short = edit(data, "binding.roles", data["binding"]["roles"][:2])
    refuses(dump(one_short), SchemaViolationError)
    refuses(
        tampered_v2("complete", "binding.roles.0.role", "other-role"),
        SchemaViolationError,
    )
    refuses(tampered_v2("complete", "binding.roles", []), SchemaViolationError)


def test_v1_missing_role_is_rejected() -> None:
    data = json.loads(v1_bytes("pair"))
    refuses(
        dump(edit(data, "selected_sources", data["selected_sources"][:1])), V1ReadError
    )
    refuses(tampered_v1("pair", "selected_sources.0.role", "other-role"), V1ReadError)


# -- negative: oversized parts and payloads --------------------------------------


def test_v2_oversized_part_and_part_count_are_rejected() -> None:
    refuses(
        tampered_v2("complete", "parts.0.data.byte_count", 4097), SchemaViolationError
    )
    refuses(
        tampered_v2("complete", "configuration.max_parts_per_unit", 1),
        SchemaViolationError,
    )
    refuses(tampered_v2("complete", "parts.1.part_index", 5), SchemaViolationError)


def test_v2_payload_above_configured_snapshot_bound_is_rejected() -> None:
    small = seal_snapshot(
        load(edit(snapshot_data(), "configuration.max_snapshot_bytes", 4096))
    )
    payload = dump(small.model_dump(mode="json"))
    check(len(payload) > 4096, "fixture is larger than the 4096 byte bound")
    refuses(payload, OversizedInputError)
    with pytest.raises(OversizedInputError):
        V2CODEC.encode(small)


def test_v1_oversized_part_budget_is_rejected() -> None:
    refuses(tampered_v1("pair", "configuration.split.max_part_bytes", 512), V1ReadError)
    refuses(
        tampered_v1("partial", "configuration.split.max_parts_per_unit", 1), V1ReadError
    )
    refuses(tampered_v1("pair", "configuration.max_snapshot_bytes", 4096), V1ReadError)


def test_oversized_payload_is_rejected_for_both_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter, "MAX_TRIAGE_INPUT_BYTES", 6000)
    refuses(v2_bytes("complete") + b" ", InputTooLargeError)
    refuses(v1_bytes("pair"), InputTooLargeError)
    monkeypatch.setattr(adapter, "MAX_TRIAGE_INPUT_BYTES", 6143)
    refuses(v2_bytes("complete") + b" ", InputTooLargeError)
    check(read_triage_input(v2_bytes("complete")).version == "2", "exact bound is fine")


# -- negative: unknown or mixed version ------------------------------------------


def test_unknown_version_is_refused_by_the_adapter() -> None:
    refuses(tampered_v1("held", "schema_version", "3"), UnsupportedVersionError)
    refuses(tampered_v1("held", "schema_version", "2"), UnsupportedVersionError)
    refuses(dump({"kind": "triage_input"}), UnsupportedVersionError)
    refuses(tampered_v2("complete", "header.version", "3"), UnknownVersionError)
    refuses(tampered_v2("complete", "header.version", "1"), UnknownVersionError)
    refuses(tampered_v2("complete", "header.kind", "prepared"), UnknownKindError)
    refuses(
        tampered_v2("complete", "binding.prepared.0.result.schema_version", "1"),
        UnknownVersionError,
    )
    refuses(
        tampered_v2("complete", "binding.rule.kind", "triage_rules_x"), UnknownKindError
    )


def test_mixed_version_payload_is_refused() -> None:
    data = json.loads(v2_bytes("complete"))
    refuses(dump({**data, "schema_version": "1"}), MixedVersionsError)
    refuses(
        dump({**json.loads(v1_bytes("held")), "header": data["header"]}),
        MixedVersionsError,
    )


def test_each_codec_refuses_the_other_version() -> None:
    with pytest.raises(HistoricalVersionError):
        V2CODEC.decode(v1_bytes("held"))
    with pytest.raises(ValueError):
        TriageInputCodec().decode(v2_bytes("complete"))
    with pytest.raises(TypeError):
        TriageInputCodec().encode(read_triage_input(v2_bytes("complete")).value)
    check(issubclass(HistoricalVersionError, TriageInputV2Error), "typed v2 error")
    check(issubclass(V1ReadError, AdapterError), "typed adapter error")


def test_upstream_family_versions_are_consistent() -> None:
    def refs(version: str) -> tuple[ResultRef, ...]:
        return tuple(
            ResultRef(f"id-{k}", k, version)
            for k in ("prepared", "filter_result", "group_result")
        )

    check(classify_upstream(refs("1")) == "1", "historical v1 family")
    check(classify_upstream(refs("2")) == "2", "v2 family")
    check(classify_upstream(()) is None, "empty family")
    with pytest.raises(MixedVersionsError):
        classify_upstream((*refs("1")[:1], *refs("2")[1:]))
    with pytest.raises(UnsupportedVersionError):
        classify_upstream(refs("3"))
