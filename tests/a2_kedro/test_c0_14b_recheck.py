"""C0-14b: the in-lock recheck verifies saved results, claims and history."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from msgloom.a2_kedro.contracts.identity import AttemptProof
from msgloom.a2_kedro.contracts.receipt import CompletionReceipt
from msgloom.contracts import Limitation, ResultRef, SemanticDataRef, TerminalStatus
from msgloom.persistence.a2_schema import acquire_claim, release_claim
from msgloom.persistence.a2_workset_finalize import (
    A2FinalizeError,
    FinalizeRequest,
    finalize_a2_intake_workset_v2,
)
from msgloom.persistence.codecs import encode_limitations, encode_semantic_data_ref
from tests.a2_kedro.helpers import WORKSET_REF, check, hexd
from tests.a2_kedro.helpers_c0_14b import (
    BATCH_REF,
    PENDING,
    Env,
    Hooked,
    attempt_proof,
    build_env,
    publish,
    refuse,
    saved_result,
    stage_for,
)

INCOMPLETE = TerminalStatus.INCOMPLETE
LIMIT = (Limitation("partial", "one transition skipped"),)
ALLOWED = frozenset(
    {
        "phase1_a2_claims",
        "phase1_a2_accepted_stages",
        "phase1_a2_stage_attempts",
        "phase1_stage_results",
        "phase1_preparation_intake_worksets",
        "phase1_schema_metadata",
        "main",  # require_schema5 reads main.sqlite_master (schema only)
    }
)
TABLE = re.compile(r"\b(?:FROM|INTO|UPDATE)\s+(\w+)")


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    yield from build_env(tmp_path)


def root_ref(env: Env) -> ResultRef:
    return env.receipt.roots[0].result


def replace(
    env: Env,
    ref: ResultRef,
    writer: AttemptProof,
    seq: int,
    status: TerminalStatus = TerminalStatus.COMPLETE,
    limitations: tuple[Limitation, ...] = (),
) -> None:
    """Publish ``ref`` again, from ``writer``, in place of the fixture stage."""
    key = (ref.result_id,)
    env.db.execute("PRAGMA foreign_keys = OFF")
    for table, column in (
        ("phase1_a2_stage_attempts", "logical_key"),
        ("phase1_a2_accepted_stages", "logical_key"),
        ("phase1_stage_results", "result_id"),
    ):
        env.db.execute(f"DELETE FROM {table} WHERE {column} = ?", key)
    stage = stage_for(ref, "a", writer, status, limitations)
    result = saved_result(ref, "a", writer, status, limitations)
    publish(env.db, stage, seq, result)
    env.accepted[ref.result_id] = stage


def incomplete_request(env: Env) -> FinalizeRequest:
    """Make the batch INCOMPLETE with a limitation; return its request."""
    batch = env.receipt.transition_batch
    if batch is None:
        pytest.fail("fixture receipt has a batch")
    replace(env, BATCH_REF, attempt_proof(), env.claim_seq, INCOMPLETE, LIMIT)
    receipt = CompletionReceipt.build(
        workset=WORKSET_REF,
        status=INCOMPLETE,
        policy_version=env.receipt.policy_version,
        roots=env.receipt.roots,
        transition_batch=batch.model_copy(update={"status": INCOMPLETE}),
    )
    return env.request(receipt=receipt)


def test_every_recheck_query_reads_metadata_only(env: Env) -> None:
    hooked = Hooked(env.db)
    finalize_a2_intake_workset_v2(hooked, env.store, env.request())  # type: ignore[arg-type]
    tables = {m.group(1) for sql in hooked.seen for m in TABLE.finditer(sql)}
    check("phase1_stage_results" in tables, "saved results are rechecked")
    check("phase1_a2_claims" in tables, "publishing claims are rechecked")
    check("phase1_a2_stage_attempts" in tables, "attempt history is rechecked")
    for sql in hooked.seen:
        check(set(TABLE.findall(sql)) <= ALLOWED, "unexpected table")
        check("phase1_semantic_data" not in sql, "payload table must not be read")
        check("payload" not in sql.lower(), "payload column must not be read")
        check("SELECT *" not in sql, "select columns by name")


def test_stage_from_an_earlier_attempt_is_accepted(env: Env) -> None:
    earlier = AttemptProof(
        execution_id="exec-a0",
        attempt_id="a0",
        claim_key="prepare:earlier-stage",
        claim_token_sha256=hexd("e"),
    )
    seq = acquire_claim(env.db, earlier)
    if seq is None:
        pytest.fail("earlier claim must be acquired")
    release_claim(env.db, seq)
    replace(env, root_ref(env), earlier, seq)
    check(env.run().outcome == "finalized", "an earlier attempt is reused")


def test_incomplete_stage_with_limitations_finalizes(env: Env) -> None:
    request = incomplete_request(env)
    result = finalize_a2_intake_workset_v2(env.db, env.store, request)
    check(result.outcome == "finalized", "outcome")
    check(env.rows()[0][1] == "incomplete", "receipt status is written")


def test_saved_stage_result_row_missing_is_refused(env: Env) -> None:
    env.db.execute(
        "DELETE FROM phase1_stage_results WHERE result_id = ?",
        (root_ref(env).result_id,),
    )
    refuse(env, "stage-result-missing")
    check(env.rows() == [PENDING], "row is still pending")


def test_saved_stage_result_sha_mismatch_is_refused(env: Env) -> None:
    other = SemanticDataRef(
        "data-" + root_ref(env).result_id[-8:],
        root_ref(env).kind,
        root_ref(env).schema_version,
        hexd("9"),
        100,
    )
    env.db.execute(
        "UPDATE phase1_stage_results SET semantic_data_ref = ? WHERE result_id = ?",
        (encode_semantic_data_ref(other), root_ref(env).result_id),
    )
    refuse(env, "stage-result-mismatch")


def test_accepted_stage_sha_column_mismatch_is_refused(env: Env) -> None:
    env.db.execute(
        "UPDATE phase1_a2_accepted_stages SET canonical_sha256 = ? "
        "WHERE logical_key = ?",
        (hexd("9"), root_ref(env).result_id),
    )
    refuse(env, "accepted-columns-mismatch")


def test_stage_result_by_another_writer_is_refused(env: Env) -> None:
    env.db.execute(
        "UPDATE phase1_stage_results SET attempt_id = 'a7' WHERE result_id = ?",
        (root_ref(env).result_id,),
    )
    refuse(env, "stage-result-writer-mismatch")


def test_stage_published_by_claim_outside_the_history_is_refused(env: Env) -> None:
    other = AttemptProof(
        execution_id="exec-b",
        attempt_id="b",
        claim_key="prepare:other-stage",
        claim_token_sha256=hexd("f"),
    )
    seq = acquire_claim(env.db, other)
    if seq is None:
        pytest.fail("other claim must be acquired")
    key = root_ref(env).result_id
    env.db.execute(
        "UPDATE phase1_a2_stage_attempts SET claim_seq = ? WHERE logical_key = ?",
        (seq, key),
    )
    refuse(env, "publish-attempt-missing")
    env.db.execute("DELETE FROM phase1_a2_stage_attempts WHERE logical_key = ?", (key,))
    refuse(env, "publish-attempt-missing")


def test_publishing_claim_row_is_checked(env: Env) -> None:
    key = root_ref(env).result_id
    env.db.execute("PRAGMA foreign_keys = OFF")
    env.db.execute(
        "UPDATE phase1_a2_accepted_stages SET writer_claim_seq = 999 "
        "WHERE logical_key = ?",
        (key,),
    )
    refuse(env, "publish-claim-missing")
    other = AttemptProof(
        execution_id="exec-b",
        attempt_id="b",
        claim_key="prepare:other-stage",
        claim_token_sha256=hexd("f"),
    )
    seq = acquire_claim(env.db, other)
    env.db.execute(
        "UPDATE phase1_a2_accepted_stages SET writer_claim_seq = ? "
        "WHERE logical_key = ?",
        (seq, key),
    )
    refuse(env, "publish-claim-mismatch")


@pytest.mark.parametrize(
    ("sql", "reason"),
    [
        (
            "UPDATE phase1_stage_results SET limitations = ? WHERE result_id = ?",
            "stage-result-mismatch",
        ),
        (
            "UPDATE phase1_stage_results SET status = 'complete' WHERE result_id = ?",
            "stage-result-corrupt",
        ),
        (
            (
                "UPDATE phase1_a2_accepted_stages SET limitations_digest = ? "
                "WHERE logical_key = ?"
            ),
            "accepted-columns-mismatch",
        ),
    ],
)
def test_status_or_limitations_that_differ_are_refused(
    env: Env, sql: str, reason: str
) -> None:
    request = incomplete_request(env)
    changed = {
        "stage-result-mismatch": encode_limitations((Limitation("other", "x"),)),
        "accepted-columns-mismatch": hexd("9"),
    }.get(reason)
    args = (changed, BATCH_REF.result_id) if changed else (BATCH_REF.result_id,)
    env.db.execute(sql, args)
    refuse(env, reason, request)


def test_complete_stage_saved_as_incomplete_is_refused(env: Env) -> None:
    env.db.execute(
        "UPDATE phase1_stage_results SET status = 'incomplete', limitations = ? "
        "WHERE result_id = ?",
        (encode_limitations(LIMIT), root_ref(env).result_id),
    )
    refuse(env, "stage-result-mismatch")


@pytest.mark.parametrize("fault", ["workset-not-pending", "readback-mismatch"])
def test_update_faults_leave_everything_unchanged(env: Env, fault: str) -> None:
    body = (
        "SELECT RAISE(IGNORE);"
        if fault == "workset-not-pending"
        else "UPDATE phase1_preparation_intake_worksets "
        "SET terminal_status = 'incomplete' WHERE result_id = NEW.result_id;"
    )
    when = "BEFORE" if fault == "workset-not-pending" else "AFTER"
    env.db.execute(
        f"CREATE TEMP TRIGGER fault {when} UPDATE ON "
        f"phase1_preparation_intake_worksets BEGIN {body} END"
    )
    refuse(env, fault)
    check(env.rows() == [PENDING], "row is still pending")
    check(env.files() == [], "no proof file before the read-back passes")
    env.db.execute("DROP TRIGGER fault")
    check(env.run().outcome == "finalized", "a retry succeeds")


def test_failed_recheck_writes_no_sql_and_no_file(env: Env) -> None:
    env.db.execute("DELETE FROM phase1_a2_stage_attempts")
    hooked = Hooked(env.db)
    with pytest.raises(A2FinalizeError) as caught:
        finalize_a2_intake_workset_v2(hooked, env.store, env.request())  # type: ignore[arg-type]
    check(caught.value.reason == "publish-attempt-missing", "reason")
    check(not any(s.startswith("UPDATE") for s in hooked.seen), "no UPDATE ran")
    check(env.files() == [], "no proof file")
