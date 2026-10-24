"""Accepted-stage record and the pure append-or-verify decision."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.contracts import Limitation, ResultRef, TerminalStatus
from msgloom.persistence.a2_acceptance_models import (
    AcceptanceConflict,
    AcceptedStage,
    accepted_stage_from_result,
    decide_append_or_verify,
)
from tests.a2_kedro.helpers import (
    accepted_ref,
    check,
    hexd,
    mutate,
    proof,
    result_for,
    stage_identity,
)


def accepted(**result_changes):
    identity = stage_identity()
    return identity, accepted_stage_from_result(
        identity, result_for(identity, **result_changes), proof()
    )


def test_record_is_derived_from_the_saved_result() -> None:
    identity, record = accepted()
    check(record.logical_key == identity.logical_key(), "key")
    check(record.output == identity.result_ref(), "ref")
    check(
        record.canonical_sha256 == "a" * 64 and record.canonical_byte_count == 100,
        "payload",
    )
    check(record.lineage_digest == identity.lineage(), "lineage")
    check(len(record.stage_metadata_sha256) == 64, "metadata sha")
    check(
        record.record_sha256() == accepted()[1].record_sha256(), "record digest stable"
    )


def test_first_write_inserts_and_equal_replay_verifies() -> None:
    _, record = accepted()
    check(decide_append_or_verify(None, record) == "insert", "insert")
    check(decide_append_or_verify(record, record) == "replay", "replay")


def test_replay_by_another_attempt_and_claim_is_equal() -> None:
    identity, first = accepted(attempt="a1")
    second = accepted_stage_from_result(
        identity, result_for(identity, attempt="a2"), proof("a2")
    )
    check(first.writer != second.writer, "different writer proofs")
    check(
        decide_append_or_verify(first, second) == "replay", "attempt is not integrity"
    )


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"sha": "b" * 64}, "canonical_sha256"),
        ({"size": 101}, "canonical_byte_count"),
        (
            {
                "status": TerminalStatus.INCOMPLETE,
                "limitations": (Limitation("l", "d"),),
            },
            "status",
        ),
    ],
)
def test_same_key_with_different_result_fails_closed(changes, field) -> None:
    _, original = accepted()
    _, other = accepted(**changes)
    with pytest.raises(AcceptanceConflict) as caught:
        decide_append_or_verify(original, other)
    check(field in caught.value.fields, f"{field} must be reported")
    check("a2-accepted-result-integrity-conflict" in str(caught.value), "message")


def test_different_limitations_with_same_bytes_conflict() -> None:
    inc = TerminalStatus.INCOMPLETE
    _, one = accepted(status=inc, limitations=(Limitation("l", "one"),))
    _, two = accepted(status=inc, limitations=(Limitation("l", "two"),))
    check(one.canonical_sha256 == two.canonical_sha256, "same payload")
    with pytest.raises(AcceptanceConflict) as caught:
        decide_append_or_verify(one, two)
    check("limitations_digest" in caught.value.fields, "limitations reported")
    check("stage_metadata_sha256" in caught.value.fields, "metadata sha reported")


def test_substituted_result_ref_conflicts() -> None:
    _, record = accepted()
    swapped = mutate(record, output=ResultRef(record.logical_key, "zones", "1"))
    with pytest.raises(AcceptanceConflict) as caught:
        decide_append_or_verify(record, swapped)
    check("output" in caught.value.fields, "output reported")


def test_conflict_report_has_field_names_only() -> None:
    _, record = accepted()
    _, other = accepted(sha="b" * 64)
    with pytest.raises(AcceptanceConflict) as caught:
        decide_append_or_verify(record, other)
    text = str(caught.value) + ",".join(caught.value.fields)
    check("b" * 64 not in text and "a" * 64 not in text, "values must not leak")


def test_foreign_key_conflicts() -> None:
    _, record = accepted()
    other = mutate(
        record,
        logical_key="a2-accepted:" + hexd("7"),
        output=ResultRef(
            "a2-accepted:" + hexd("7"), record.output.kind, record.output.schema_version
        ),
    )
    with pytest.raises(AcceptanceConflict):
        decide_append_or_verify(record, other)


def test_record_shape_negative_cases() -> None:
    _, record = accepted()
    with pytest.raises(ValueError, match="invalid logical key"):
        mutate(record, logical_key="plain-key")
    with pytest.raises(ValueError, match="carry the logical key"):
        mutate(record, output=accepted_ref("9", "frozen_source_selection", "1"))
    with pytest.raises(ValueError, match="read-only"):
        mutate(record, output=ResultRef(record.logical_key, "prepared", "1"))
    with pytest.raises(ValueError, match="not approved"):
        mutate(record, output=ResultRef(record.logical_key, "prepared", "3"))
    with pytest.raises(ValueError, match="complete or incomplete"):
        mutate(record, status="failed")
    with pytest.raises(ValueError):
        mutate(record, canonical_byte_count=0)
    with pytest.raises(ValueError):
        mutate(record, canonical_byte_count=64 * 1024 * 1024 + 1)
    with pytest.raises(ValueError):
        mutate(record, canonical_sha256="short")
    with pytest.raises(ValueError):
        mutate(record, stage_metadata_sha256="G" * 64)
    check(isinstance(record, AcceptedStage), "type")


def test_builder_rejects_lineage_or_identity_mismatch() -> None:
    identity = stage_identity()
    with pytest.raises(A2ContractError):
        accepted_stage_from_result(
            identity,
            result_for(identity, result_id="a2-accepted:" + hexd("0")),
            proof(),
        )
    with pytest.raises(A2ContractError):
        accepted_stage_from_result(
            identity, result_for(identity, acceptable=False), proof()
        )
