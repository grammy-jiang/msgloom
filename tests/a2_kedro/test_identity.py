"""Input-only stage identity, lineage, attempt proof and metadata digests."""

from __future__ import annotations

from typing import Any

import pytest

from msgloom.a2_kedro.contracts.codec import A2ContractError
from msgloom.a2_kedro.contracts.identity import (
    AttemptProof,
    check_stage_matches_identity,
    lineage_digest,
    stage_metadata,
    status_limitations_digest,
)
from msgloom.contracts import (
    Limitation,
    ResultRef,
    TerminalStatus,
    VersionRef,
)
from tests.a2_kedro.helpers import (
    CONFIG,
    WORKSET_REF,
    accepted_ref,
    check,
    claim,
    hexd,
    mutate,
    proof,
    result_for,
    root_for,
    stage_identity,
    transition_for,
    workset,
)

GOLDEN_KEY = (
    "a2-accepted:40eca2e4dbbee7a1b677713e59dc56c41ed8244d58baedd720b4a8fd00743c7a"
)


def downstream(**changes: Any):
    """Return a non-root stage that depends on one accepted upstream."""
    values: dict[str, Any] = {
        "stage_kind": "parsed_parts",
        "upstream": (accepted_ref("1"),),
    }
    values.update(changes)
    return stage_identity(**values)


def test_key_is_deterministic_and_pinned() -> None:
    check(stage_identity().logical_key() == stage_identity().logical_key(), "stable")
    check(stage_identity().logical_key() == GOLDEN_KEY, "golden key changed")
    ref = stage_identity().result_ref()
    check(ref.result_id == GOLDEN_KEY and ref.kind == "frozen_source_selection", "ref")


@pytest.mark.parametrize(
    "changes",
    [
        {"scope_key": hexd("6")},
        {"partition_ordinal": 1},
        {"configuration_version": "config-2"},
        {"code_version": "code-2"},
        {"parser_version": "parser-2"},
        {"rule_version": "rule-2"},
        {"partition_policy_version": "part-2"},
        {"workset": ResultRef("other", "preparation_intake_workset", "1")},
        {"upstream": (accepted_ref("2"),)},
        {"upstream": (accepted_ref("1"), accepted_ref("2"))},
        {"upstream": (accepted_ref("2"), accepted_ref("1"))},
    ],
)
def test_every_frozen_input_changes_the_key(changes: dict[str, Any]) -> None:
    check(
        downstream().logical_key() != downstream(**changes).logical_key(),
        f"key ignored {sorted(changes)}",
    )


def test_selected_root_changes_the_key() -> None:
    ws = workset(2)
    check(
        stage_identity(selected=(root_for(ws, 0),)).logical_key()
        != stage_identity(selected=(root_for(ws, 1),)).logical_key(),
        "root choice must change key",
    )


def test_key_has_no_attempt_output_or_time_input() -> None:
    for field in (
        "execution_id",
        "attempt_id",
        "output_sha256",
        "created_at",
        "node_name",
    ):
        with pytest.raises(ValueError):
            mutate(stage_identity(), **{field: "x"})
    names = set(stage_identity().model_dump())
    check(not names & {"execution", "attempt", "claim", "sha256", "status"}, "fields")


def test_attempts_share_key_and_have_separate_proofs() -> None:
    identity = stage_identity()
    first = result_for(identity, attempt="a1")
    second = result_for(identity, attempt="a2")
    check(first.result_id == second.result_id, "same logical result id")
    check(
        stage_metadata(first).digest() == stage_metadata(second).digest(),
        "attempt-free",
    )
    check(proof("a1") != proof("a2"), "attempt proofs differ")


def test_attempt_proof_never_stores_the_raw_token() -> None:
    stored = proof().model_dump_json()
    check("secret-1" not in stored, "raw claim token leaked")
    check(
        AttemptProof.from_claim(claim(token="t1")).claim_token_sha256
        != AttemptProof.from_claim(claim(token="t2")).claim_token_sha256,
        "token digest must depend on token",
    )


def test_full_upstream_lineage() -> None:
    chain = (accepted_ref("1"), accepted_ref("2", "parsed_parts"))
    check(lineage_digest(chain) != lineage_digest(chain[::-1]), "order matters")
    check(lineage_digest(chain) != lineage_digest(chain[:1]), "length matters")
    check(downstream().lineage() == lineage_digest((accepted_ref("1"),)), "identity")


@pytest.mark.parametrize(
    "bad",
    [
        (ResultRef("plain-id", "parsed_parts", "1"),),
        (accepted_ref("1"), accepted_ref("1")),
        (accepted_ref("1", "prepared", "1"),),
        (accepted_ref("1", "unknown_kind", "1"),),
        (accepted_ref("1", "prepared", "9"),),
    ],
)
def test_bad_upstream_rejected(bad: tuple[ResultRef, ...]) -> None:
    with pytest.raises(A2ContractError):
        lineage_digest(bad)
    with pytest.raises(ValueError):
        downstream(upstream=bad)


def test_stage_graph_rules() -> None:
    with pytest.raises(ValueError, match="accepted upstream"):
        stage_identity(stage_kind="parsed_parts")
    with pytest.raises(ValueError, match="cannot have upstream"):
        stage_identity(upstream=(accepted_ref("1"),))
    with pytest.raises(ValueError, match="read-only"):
        stage_identity(stage_kind="prepared", schema_version="1")
    with pytest.raises(ValueError, match="read-only"):
        downstream(stage_kind="prepared", schema_version="1")
    with pytest.raises(ValueError, match="not approved"):
        downstream(stage_kind="prepared", schema_version="3")
    with pytest.raises(ValueError, match="not approved"):
        downstream(stage_kind="made_up")
    with pytest.raises(ValueError, match="schema mismatch"):
        stage_identity(workset=ResultRef("w", "other", "1"))
    with pytest.raises(ValueError, match="roots, not transitions"):
        stage_identity(selected=())


def test_prepared_v2_is_approved_and_transitions_form_one_ordered_batch() -> None:
    check(
        downstream(stage_kind="prepared", schema_version="2").schema_version == "2",
        "v2",
    )
    batch = (transition_for(1, "c"), transition_for(1, "d"))
    kwargs: dict[str, Any] = {
        "stage_kind": "prepared_transitions",
        "schema_version": "2",
        "selected": (),
        "upstream": (accepted_ref("1"),),
    }
    one = stage_identity(transitions=batch, **kwargs)
    check(
        one.logical_key()
        != stage_identity(transitions=batch[::-1], **kwargs).logical_key(),
        "order",
    )
    check(
        one.logical_key()
        != stage_identity(transitions=batch[:1], **kwargs).logical_key(),
        "all",
    )
    with pytest.raises(ValueError, match="duplicate exact transition"):
        stage_identity(transitions=(batch[0], batch[0]), **kwargs)
    with pytest.raises(ValueError, match="only a batch"):
        stage_identity(
            transitions=batch, **{**kwargs, "selected": (root_for(workset(1)),)}
        )
    with pytest.raises(ValueError, match="only a batch"):
        stage_identity(**kwargs)


def test_duplicate_or_mixed_roots_rejected() -> None:
    root = root_for(workset(1))
    with pytest.raises(ValueError, match="duplicate selected"):
        stage_identity(selected=(root, root))


def test_status_limitations_digest() -> None:
    a, b = Limitation("x", "1"), Limitation("y", "2")
    inc = TerminalStatus.INCOMPLETE
    check(
        status_limitations_digest(inc, (a, b))
        == status_limitations_digest(inc, (b, a)),
        "limitations are a set",
    )
    check(
        status_limitations_digest(inc, (a,)) != status_limitations_digest(inc, (a, b)),
        "set content matters",
    )
    check(
        status_limitations_digest(inc, ())
        != status_limitations_digest(TerminalStatus.COMPLETE, ()),
        "status matters",
    )
    with pytest.raises(A2ContractError, match="duplicate"):
        status_limitations_digest(inc, (a, a))
    with pytest.raises(A2ContractError, match="cannot carry"):
        status_limitations_digest(TerminalStatus.COMPLETE, (a,))
    for status in (
        TerminalStatus.FAILED,
        TerminalStatus.BLOCKED,
        TerminalStatus.CANCELLED,
    ):
        with pytest.raises(A2ContractError):
            status_limitations_digest(status, ())


def test_metadata_digest_covers_status_limitations_and_versions() -> None:
    identity = stage_identity()
    base = stage_metadata(result_for(identity)).digest()
    inc = result_for(
        identity, status=TerminalStatus.INCOMPLETE, limitations=(Limitation("l", "d"),)
    )
    other_limit = result_for(
        identity, status=TerminalStatus.INCOMPLETE, limitations=(Limitation("l", "e"),)
    )
    versions = result_for(identity, source_versions=(VersionRef("k", "i", "v"),))
    rule = result_for(identity, rule_version="rule-x")
    digests = {
        base,
        *(stage_metadata(r).digest() for r in (inc, other_limit, versions, rule)),
    }
    check(len(digests) == 5, "each metadata change must change the digest")


def test_metadata_rejects_unacceptable_or_unsaved_results() -> None:
    identity = stage_identity()
    with pytest.raises(A2ContractError, match="not an acceptable"):
        stage_metadata(result_for(identity, acceptable=False))
    with pytest.raises(A2ContractError, match="semantic data"):
        stage_metadata(result_for(identity, semantic_data_ref=None))
    failed = result_for(identity, status=TerminalStatus.FAILED, acceptable=False)
    with pytest.raises(A2ContractError):
        stage_metadata(failed)


def test_saved_result_must_match_frozen_identity() -> None:
    identity = stage_identity()
    check_stage_matches_identity(identity, result_for(identity))
    mismatches: list[dict[str, Any]] = [
        {"result_id": "a2-accepted:" + hexd("0")},
        {"configuration_version": CONFIG + "x"},
        {"input_refs": (accepted_ref("1"),)},
        {"code_version": "other"},
    ]
    for changes in mismatches:
        with pytest.raises(A2ContractError):
            check_stage_matches_identity(identity, result_for(identity, **changes))
    check(WORKSET_REF.kind == "preparation_intake_workset", "fixture sanity")
