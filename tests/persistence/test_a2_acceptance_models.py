"""C0-12a: closed schema allowlist, input-only key, digest and size checks."""

from __future__ import annotations

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.identity import StageIdentity, stage_metadata
from msgloom.a2_kedro.contracts.schema_ids import (
    HISTORICAL_READ_ONLY,
    RECEIPT_SCHEMA,
    STAGE_SCHEMAS,
)
from msgloom.contracts import Limitation, ResultRef, TerminalStatus
from msgloom.persistence.a2_acceptance_models import (
    MAX_PAYLOAD_BYTES,
    AcceptanceConflict,
    AcceptedStage,
    accepted_stage_from_result,
    verify_accepted_stage,
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

KEY = "a2-accepted:" + hexd("1")


def record_for(ref: ResultRef, **changes) -> AcceptedStage:
    """Build a record directly, so any kind/version can be tried."""
    values = {
        "logical_key": ref.result_id,
        "output": ref,
        "canonical_sha256": hexd("a"),
        "canonical_byte_count": 10,
        "semantic_data_id": "data-1",
        "stage_metadata_sha256": hexd("b"),
        "lineage_digest": hexd("c"),
        "status": TerminalStatus.COMPLETE,
        "limitations_digest": hexd("d"),
        "writer": proof(),
    }
    values.update(changes)
    return AcceptedStage(**values)


def built(identity: StageIdentity | None = None, **result_changes):
    identity = identity or stage_identity()
    result = result_for(identity, **result_changes)
    return identity, result, accepted_stage_from_result(identity, result, proof())


# --- closed kind/version allowlist -------------------------------------


@pytest.mark.parametrize(("kind", "version"), sorted(STAGE_SCHEMAS.items()))
def test_every_approved_pair_is_accepted(kind: str, version: str) -> None:
    record = record_for(ResultRef(KEY, kind, version))
    check(record.output.kind == kind, "approved pair stored")


@pytest.mark.parametrize(("kind", "version"), sorted(HISTORICAL_READ_ONLY))
def test_old_v1_kinds_are_rejected_as_read_only(kind: str, version: str) -> None:
    with pytest.raises(ValueError, match="read-only"):
        record_for(ResultRef(KEY, kind, version))


@pytest.mark.parametrize(
    ("kind", "version"),
    [
        ("prepared", "3"),
        ("prepared", "02"),
        ("prepared", " 2"),
        ("prepared", "2 "),
        ("prepared", ""),
        ("zones", "2"),
        ("frozen_source_selection", "2"),
        ("triage_input", "1"),
        ("triage_input", "2"),
        (RECEIPT_SCHEMA[0], RECEIPT_SCHEMA[1]),
        ("Prepared", "2"),
        ("unknown_kind", "1"),
        ("", "1"),
    ],
)
def test_unapproved_pairs_are_rejected(kind: str, version: str) -> None:
    with pytest.raises(ValueError):
        record_for(ResultRef(KEY, kind, version))


def test_builder_and_identity_reject_prepared_v1() -> None:
    identity = stage_identity()
    result = result_for(identity, kind="prepared", schema_version="1")
    with pytest.raises(A2ContractError, match="not approved"):
        accepted_stage_from_result(identity, result, proof())
    with pytest.raises(ValueError, match="read-only"):
        stage_identity(
            stage_kind="prepared",
            schema_version="1",
            selected=stage_identity().selected,
            upstream=(accepted_ref("2"),),
        )


@pytest.mark.parametrize(
    "status", [s for s in TerminalStatus if s.value not in ("complete", "incomplete")]
)
def test_only_complete_or_incomplete_can_be_accepted(status) -> None:
    with pytest.raises(ValueError, match="complete or incomplete"):
        record_for(ResultRef(KEY, "zones", "1"), status=status)


# --- input-only logical key ---------------------------------------------


def test_key_ignores_output_digest_size_status_and_attempt() -> None:
    identity, _, base = built()
    other_inc = built(
        identity,
        sha="e" * 64,
        size=999,
        attempt="a9",
        status=TerminalStatus.INCOMPLETE,
        limitations=(Limitation("l", "d"),),
    )[2]
    check(base.logical_key == other_inc.logical_key, "key must be input-only")
    check(base.logical_key == identity.logical_key(), "key from identity")
    check(base.canonical_sha256 != other_inc.canonical_sha256, "outputs differ")


@pytest.mark.parametrize(
    "changes",
    [
        {"configuration_version": "config-2"},
        {"code_version": "code-2"},
        {"parser_version": "parser-2"},
        {"rule_version": "rule-2"},
        {"partition_policy_version": "part-2"},
        {"partition_ordinal": 1},
        {"scope_key": hexd("6")},
    ],
)
def test_key_changes_when_a_frozen_input_changes(changes) -> None:
    check(
        stage_identity().logical_key() != stage_identity(**changes).logical_key(),
        f"key must change for {changes}",
    )


def test_key_cannot_equal_an_output_digest() -> None:
    digest = KEY.removeprefix("a2-accepted:")
    for field in (
        "canonical_sha256",
        "stage_metadata_sha256",
        "lineage_digest",
        "limitations_digest",
    ):
        with pytest.raises(ValueError, match="must not equal an output digest"):
            record_for(ResultRef(KEY, "zones", "1"), **{field: digest})


def test_key_shape_and_output_binding_are_enforced() -> None:
    for bad in ("plain", "a2-accepted:" + "A" * 64, "a2-accepted:" + hexd("1") + "\n"):
        with pytest.raises(ValueError):
            record_for(ResultRef(bad, "zones", "1"))
    with pytest.raises(ValueError, match="carry the logical key"):
        record_for(ResultRef(KEY, "zones", "1"), logical_key="a2-accepted:" + hexd("2"))


# --- StageResult metadata SHA -------------------------------------------


def test_metadata_sha_is_the_digest_of_the_saved_result() -> None:
    identity, result, record = built()
    check(record.stage_metadata_sha256 == stage_metadata(result).digest(), "sha")
    verify_accepted_stage(record, identity, result)
    _, _, retry = built(identity, attempt="a2")
    check(
        retry.stage_metadata_sha256 == record.stage_metadata_sha256,
        "attempt must not change the metadata sha",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"sha": "e" * 64},
        {"size": 101},
        {"configuration_version": "config-x"},
        {"code_version": "code-x"},
        {"rule_version": "rule-x"},
        {
            "status": TerminalStatus.INCOMPLETE,
            "limitations": (Limitation("l", "d"),),
        },
    ],
)
def test_metadata_sha_changes_with_status_versions_and_payload(changes) -> None:
    identity = stage_identity()
    base = built(identity)[2]
    result_changes = dict(changes)
    if "configuration_version" in result_changes or "code_version" in result_changes:
        # Versions are part of the key; a different result under one key
        # must be caught by verification instead.
        result = result_for(identity, **result_changes)
        with pytest.raises(A2ContractError):
            accepted_stage_from_result(identity, result, proof())
        return
    other = built(identity, **result_changes)[2]
    check(
        other.stage_metadata_sha256 != base.stage_metadata_sha256,
        f"metadata sha unchanged for {changes}",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("stage_metadata_sha256", hexd("f")),
        ("lineage_digest", hexd("f")),
        ("canonical_sha256", hexd("f")),
        ("canonical_byte_count", 11),
        ("limitations_digest", hexd("f")),
        ("semantic_data_id", "other-data"),
    ],
)
def test_verify_rejects_a_record_that_disagrees_with_the_result(field, value) -> None:
    identity, result, record = built()
    tampered = mutate(record, **{field: value})
    with pytest.raises(AcceptanceConflict) as caught:
        verify_accepted_stage(tampered, identity, result)
    check(field in caught.value.fields, f"{field} must be reported")
    check(str(value) not in str(caught.value), "value must not be reported")


def test_verify_rejects_a_foreign_key_and_ignores_the_writer() -> None:
    identity, result, record = built()
    other_writer = mutate(record, writer=proof("a7"))
    verify_accepted_stage(other_writer, identity, result)
    foreign = mutate(
        record,
        logical_key="a2-accepted:" + hexd("7"),
        output=ResultRef("a2-accepted:" + hexd("7"), record.output.kind, "1"),
    )
    with pytest.raises(AcceptanceConflict) as caught:
        verify_accepted_stage(foreign, identity, result)
    check("logical_key" in caught.value.fields, "foreign key reported")


# --- payload and digest bounds ------------------------------------------

BAD_DIGESTS = [
    "",
    "a" * 63,
    "a" * 65,
    "A" * 64,
    "g" * 64,
    "a" * 63 + "G",
    "a" * 64 + "\n",
    "\n" + "a" * 64,
    " " + "a" * 63,
    "a" * 63 + "١",
    "ａ" * 64,
    "a" * 32 + "\x00" + "a" * 31,
]


@pytest.mark.parametrize(
    "field",
    [
        "canonical_sha256",
        "stage_metadata_sha256",
        "lineage_digest",
        "limitations_digest",
    ],
)
@pytest.mark.parametrize("bad", BAD_DIGESTS)
def test_digest_fields_need_64_lowercase_hex(field: str, bad: str) -> None:
    ref = ResultRef(KEY, "zones", "1")
    with pytest.raises(ValueError):
        record_for(ref, **{field: bad})


@pytest.mark.parametrize("bad", BAD_DIGESTS)
def test_writer_claim_digest_needs_64_lowercase_hex(bad: str) -> None:
    good = record_for(ResultRef(KEY, "zones", "1"))
    with pytest.raises(ValueError):
        mutate(good, writer={**good.writer.model_dump(), "claim_token_sha256": bad})


@pytest.mark.parametrize("size", [0, -1, MAX_PAYLOAD_BYTES + 1, True, "10", 1.5, None])
def test_payload_size_bounds_are_enforced(size) -> None:
    with pytest.raises(ValueError):
        record_for(ResultRef(KEY, "zones", "1"), canonical_byte_count=size)


def test_payload_size_edges_are_accepted() -> None:
    ref = ResultRef(KEY, "zones", "1")
    for size in (1, MAX_PAYLOAD_BYTES):
        check(
            record_for(ref, canonical_byte_count=size).canonical_byte_count == size,
            "edge",
        )


def test_record_is_bounded_and_extra_fields_are_refused() -> None:
    record = record_for(ResultRef(KEY, "zones", "1"))
    check(len(record.record_bytes()) < 16 * 1024, "record stays small")
    with pytest.raises(ValueError):
        mutate(record, semantic_data_id="d" * 2049)
    with pytest.raises(ValueError):
        AcceptedStage.model_validate({**record.model_dump(mode="json"), "extra": 1})
