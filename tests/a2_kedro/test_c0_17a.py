"""C0-17a: strict ``triage_input@2`` models. Synthetic data only."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from typing import Any

import pytest
from pydantic import ValidationError

from msgloom.a2_kedro.contracts.header import StageHeader
from msgloom.contracts import ResultRef, SemanticDataRef, VersionRef
from msgloom.triage_input import TriageInputCodec, build_triage_input
from msgloom.triage_input import TriageInputSnapshot as V1Snapshot
from msgloom.triage_input.canonical import digest
from msgloom.triage_input.integrity import selection_binding_digest
from msgloom.triage_input.models_v2 import (
    HeldReason,
    PartState,
    SelectedRole,
    TriageInputSnapshot,
)
from tests.a2_kedro.helpers import check, hexd
from tests.triage_input.helpers import config, record, selection

SECRET = "alice.private@example.invalid"
BAD = (ValueError, ValidationError)


def rref(char: str, kind: str = "prepared", version: str = "2") -> dict[str, str]:
    """Return an accepted result ref as JSON data."""
    return {
        "result_id": "a2-accepted:" + hexd(char),
        "kind": kind,
        "schema_version": version,
    }


def dref(char: str, kind: str, version: str = "2", size: int = 100) -> dict[str, Any]:
    """Return a semantic data ref as JSON data."""
    return {
        "data_id": "data-" + char,
        "kind": kind,
        "schema_version": version,
        "sha256": hexd(char),
        "byte_count": size,
    }


def vref(kind: str, version: str = "v1") -> dict[str, str]:
    return {"kind": kind, "identity": "synthetic", "version": version}


def bound(char: str, kind: str) -> dict[str, Any]:
    return {"result": rref(char, kind, "2"), "data": dref(char, kind)}


def part(index: int, unit: str = "7") -> dict[str, Any]:
    char = "de"[index]
    return {
        "part_id": hexd(char),
        "unit_id": hexd(unit),
        "unit_sha256": hexd("8"),
        "part_index": index,
        "data": {**dref(char, "triage_input_part"), "data_id": hexd(char)},
        "state": "pending",
    }


def snapshot_data() -> dict[str, Any]:
    """Three sources: a and b active in one unit, c held. Digests are 0."""
    return {
        "header": StageHeader(kind="triage_input", version="2").model_dump(mode="json"),
        "binding": {
            "prepared": [bound(c, "prepared") for c in "abc"],
            "filters": [bound(c, "filter_result") for c in "abc"],
            "groups": [bound("f", "group_result")],
            "rule": dref("9", "triage_rules"),
            "roles": [
                {"prepared": rref("a"), "role": "new-source"},
                {"prepared": rref("b"), "role": "baseline-context"},
                {"prepared": rref("c"), "role": "earlier-context"},
            ],
            "working_context": vref("working_context"),
            "versions": {
                "prompt": vref("prompt"),
                "model": vref("model"),
                "output_schema": vref("output_schema"),
                "configuration": vref("triage_input_config"),
            },
        },
        "binding_sha256": hexd("0"),
        "configuration": {
            "version": vref("triage_input_config"),
            "remove_exact_text_repetitions": False,
            "max_part_bytes": 4096,
            "max_parts_per_unit": 8,
            "max_snapshot_bytes": 1_000_000,
        },
        "configuration_sha256": hexd("0"),
        "held": [
            {
                "prepared": rref("c"),
                "role": "earlier-context",
                "reasons": ["filter-excluded", "filter-unknown"],
                "filter": rref("c", "filter_result"),
                "rule": dref("9", "triage_rules"),
            }
        ],
        "units": [
            {
                "unit_id": hexd("7"),
                "unit_sha256": hexd("8"),
                "commitment": "complete-content",
                "prepared": [rref("a"), rref("b")],
                "group": rref("f", "group_result"),
                "occurrence_count": 12,
                "occurrences_sha256": hexd("6"),
            }
        ],
        "parts": [part(0), part(1)],
        "failures": [],
        "limitations": [],
        "complete": True,
        "snapshot_sha256": hexd("0"),
    }


def load(data: dict[str, Any]) -> TriageInputSnapshot:
    """Validate ``data`` through the strict JSON path."""
    return TriageInputSnapshot.model_validate_json(json.dumps(data), strict=True)


def make_snapshot(data: dict[str, Any] | None = None) -> TriageInputSnapshot:
    """Return a valid snapshot. Digests are not sealed here (see C0-17b)."""
    return load(data or snapshot_data())


def edit(data: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    """Return a deep copy of ``data`` with the dotted ``path`` replaced."""
    out = deepcopy(data)
    target: Any = out
    *parents, last = path.split(".")
    for key in parents:
        target = target[int(key)] if isinstance(target, list) else target[key]
    if isinstance(target, list):
        target[int(last)] = value
    else:
        target[last] = value
    return out


def incomplete_data() -> dict[str, Any]:
    """A snapshot whose unit exhausted its part budget."""
    data = snapshot_data()
    data["units"][0]["commitment"] = "retained-prefix"
    data["failures"] = [
        {
            "unit_id": hexd("7"),
            "reason": "part-count-exceeded",
            "first_occurrence": 5,
            "first_text_offset": None,
            "remaining_occurrences": 7,
            "remaining_sha256": hexd("5"),
        }
    ]
    data["limitations"] = [{"code": "coverage_incomplete", "detail": "unit"}]
    data["complete"] = False
    return data


def test_valid_snapshot_and_new_roles_and_states() -> None:
    snap = make_snapshot()
    check(snap.header.kind == "triage_input", "header kind")
    check(snap.header.version == "2", "header version")
    roles = {item.role for item in snap.binding.roles}
    check(SelectedRole.BASELINE_CONTEXT in roles, "new baseline role")
    check(HeldReason.FILTER_UNKNOWN in snap.held[0].reasons, "new held reason")
    check(all(p.state is PartState.PENDING for p in snap.parts), "parts pending")
    check(make_snapshot(incomplete_data()).complete is False, "incomplete valid")


def test_wire_field_names_are_pinned() -> None:
    dumped = make_snapshot().model_dump(mode="json")
    check(
        set(dumped)
        == {
            "header",
            "binding",
            "binding_sha256",
            "configuration",
            "configuration_sha256",
            "held",
            "units",
            "parts",
            "failures",
            "limitations",
            "complete",
            "snapshot_sha256",
        },
        "snapshot fields",
    )
    check(
        set(dumped["binding"])
        == {
            "prepared",
            "filters",
            "groups",
            "rule",
            "roles",
            "working_context",
            "versions",
        },
        "binding fields",
    )
    check("schema_version" not in dumped, "no v1 schema_version field")


def test_models_are_frozen_strict_and_forbid_extra() -> None:
    snap = make_snapshot()
    with pytest.raises(BAD):
        snap.complete = False  # type: ignore[misc]
    with pytest.raises(BAD):
        load({**snapshot_data(), "extra": 1})
    with pytest.raises(BAD):
        load(edit(snapshot_data(), "binding.versions.extra", 1))
    with pytest.raises(BAD):
        load(edit(snapshot_data(), "configuration.max_part_bytes", True))
    with pytest.raises(BAD):
        load(edit(snapshot_data(), "configuration.max_part_bytes", 4096.0))
    with pytest.raises(BAD):
        TriageInputSnapshot.model_validate({"complete": "yes"}, strict=True)


MUTATIONS = [
    ("header.version", "1"),
    ("header.kind", "prepared"),
    ("binding.prepared.0.result.schema_version", "1"),
    ("binding.prepared.0.result.result_id", "plain-id"),
    ("binding.prepared.0.data.kind", "filter_result"),
    ("binding.filters.0.result.kind", "prepared"),
    ("binding.groups.0.data.schema_version", "1"),
    ("binding.rule.schema_version", "1"),
    ("binding.rule.kind", "prepared"),
    ("binding.roles.0.role", "baseline"),
    ("binding.roles.0.prepared", rref("d")),
    ("binding.prepared", [bound("b", "prepared"), bound("a", "prepared")]),
    ("binding.prepared", [bound("a", "prepared"), bound("a", "prepared")]),
    ("binding.prepared", []),
    ("binding.versions.configuration", vref("triage_input_config", "other")),
    ("held.0.reasons", ["filter-unknown", "filter-excluded"]),
    ("held.0.reasons", ["spam"]),
    ("held.0.reasons", []),
    ("held.0.role", "new-source"),
    ("held.0.filter", rref("1", "filter_result")),
    ("held.0.rule", dref("8", "triage_rules")),
    ("held", []),
    ("units.0.commitment", "retained-prefix"),
    ("units.0.prepared", [rref("a"), rref("c")]),
    ("units.0.group", rref("1", "group_result")),
    ("units.0.occurrence_count", 0),
    ("units.0.unit_id", "ABC"),
    ("parts.0.state", "done"),
    ("parts.0.data.data_id", "other"),
    ("parts.0.data.kind", "triage_input_part_x"),
    ("parts.0.unit_sha256", hexd("1")),
    ("parts.0.unit_id", hexd("1")),
    ("parts.1.part_index", 3),
    ("parts.0.data.byte_count", 5000),
    ("limitations", [{"code": "x", "detail": "y"}]),
    ("complete", False),
    ("binding_sha256", "A" * 64),
    ("configuration.version", vref("triage_input_config", "other")),
    ("configuration.max_snapshot_bytes", 10),
    ("binding.working_context.identity", "a\nb"),
]


@pytest.mark.parametrize(("path", "value"), MUTATIONS)
def test_each_mutation_is_rejected(path: str, value: Any) -> None:
    with pytest.raises(BAD):
        load(edit(snapshot_data(), path, value))


def test_incomplete_needs_failure_limitation_and_unit_commitment() -> None:
    for path, value in (
        ("limitations", []),
        ("complete", True),
        ("failures", []),
        ("failures.0.remaining_occurrences", 6),
        ("failures.0.unit_id", hexd("1")),
    ):
        with pytest.raises(BAD):
            load(edit(incomplete_data(), path, value))


def test_duplicate_part_ids_and_unsorted_parts_are_rejected() -> None:
    dup = snapshot_data()
    dup["parts"][1]["part_id"] = dup["parts"][0]["part_id"]
    dup["parts"][1]["data"]["data_id"] = dup["parts"][0]["part_id"]
    with pytest.raises(BAD):
        load(dup)
    swapped = snapshot_data()
    swapped["parts"].reverse()
    with pytest.raises(BAD):
        load(swapped)


def test_validation_errors_never_echo_input_values() -> None:
    data = edit(snapshot_data(), "binding.versions.prompt.identity", SECRET + "\n")
    # Field names (loc) can still appear in pydantic text; the codec drops them.
    with pytest.raises(ValidationError) as caught:
        load(data)
    check(SECRET not in str(caught.value), "pydantic text hides values")
    check(SECRET not in repr(caught.value.errors(include_input=False)), "no input")


def test_v1_reader_cannot_read_v2_payloads_or_refs() -> None:
    payload = json.dumps(make_snapshot().model_dump(mode="json")).encode()
    with pytest.raises(BAD):
        V1Snapshot.model_validate_json(payload, strict=True)
    with pytest.raises(BAD):
        TriageInputCodec().decode(payload)
    with pytest.raises(TypeError):
        TriageInputCodec().encode(make_snapshot())
    check(TriageInputCodec.schema_version == "1", "v1 stays at version 1")
    check(TriageInputSnapshot.model_fields["header"] is not None, "v2 has header")
    check("schema_version" not in TriageInputSnapshot.model_fields, "v2 not v1 shape")


def test_v1_codec_rejects_v2_ref_kind_version_even_when_rehashed() -> None:

    v1 = build_triage_input(selection((record("one"),)), config())
    check(TriageInputCodec().encode(v1) is not None, "control: v1 encodes")

    def rehash(snap: Any) -> Any:
        binding = selection_binding_digest(
            selection_hash=snap.selection_hash,
            selected_sources=snap.selected_sources,
            prepared_refs=snap.prepared_refs,
            filter_refs=snap.filter_refs,
            group_refs=snap.group_refs,
            rule_ref=snap.rule_ref,
            working_context_ref=snap.working_context_ref,
            versions=snap.versions,
        )
        snap = snap.model_copy(update={"selection_binding_hash": binding})
        body = snap.model_dump(mode="json", round_trip=True)
        body["snapshot_hash"] = ""
        return snap.model_copy(update={"snapshot_hash": digest(body)})

    v2_ref = replace(v1.prepared_refs[0], schema_version="2")
    check(TriageInputCodec().encode(rehash(v1)) is not None, "control: rehash ok")
    with pytest.raises(TypeError):
        TriageInputCodec().encode(
            rehash(v1.model_copy(update={"prepared_refs": (v2_ref,)}))
        )


def test_ref_types_are_the_shared_dataclasses() -> None:
    snap = make_snapshot()
    ref = snap.binding.prepared[0]
    check(isinstance(ref.result, ResultRef), "result ref type")
    check(isinstance(ref.data, SemanticDataRef), "data ref type")
    check(isinstance(snap.binding.working_context, VersionRef), "version ref type")
