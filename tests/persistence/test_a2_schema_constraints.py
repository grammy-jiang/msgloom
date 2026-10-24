"""A2 table constraints (FK, unique, CHECK, size bounds) and the claim race."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest

from msgloom.a2_kedro.contracts.schema_ids import STAGE_SCHEMAS
from msgloom.persistence.a2_acceptance_models import (
    MAX_PAYLOAD_BYTES,
    MAX_RECORD_BYTES,
    AcceptedStage,
    accepted_stage_from_result,
)
from msgloom.persistence.a2_schema import (
    A2SchemaError,
    acquire_claim,
    connect_existing,
    release_claim,
)
from tests.a2_kedro.helpers import check, hexd, proof, result_for, stage_identity
from tests.persistence.test_a2_schema_fixtures import build_schema5, raw

STAGE_COLUMNS = (
    "logical_key, kind, schema_version, status, canonical_sha256, "
    "canonical_byte_count, semantic_data_id, stage_metadata_sha256, "
    "lineage_digest, limitations_digest, writer_claim_seq, record_sha256, "
    "record_json"
)
KEY = "a2-accepted:" + hexd("1")


@pytest.fixture
def db(tmp_path: Path):
    connection = raw(build_schema5(tmp_path / "a2.sqlite"))
    acquire_claim(connection, proof("w1"))
    yield connection
    connection.close()


def stage_row(**changes) -> dict[str, object]:
    row: dict[str, object] = {
        "logical_key": KEY,
        "kind": "frozen_source_selection",
        "schema_version": "1",
        "status": "complete",
        "canonical_sha256": hexd("a"),
        "canonical_byte_count": 10,
        "semantic_data_id": "data-1",
        "stage_metadata_sha256": hexd("b"),
        "lineage_digest": hexd("c"),
        "limitations_digest": hexd("d"),
        "writer_claim_seq": 1,
        "record_sha256": hexd("e"),
        "record_json": "{}",
    }
    row.update(changes)
    return row


def put(db: sqlite3.Connection, **changes) -> None:
    row = stage_row(**changes)
    db.execute(
        f"INSERT INTO phase1_a2_accepted_stages ({STAGE_COLUMNS}) "
        f"VALUES ({', '.join('?' for _ in row)})",
        tuple(row.values()),
    )


def attempt(db: sqlite3.Connection, key=KEY, claim=1, outcome="inserted", fields=None):
    db.execute(
        "INSERT INTO phase1_a2_stage_attempts "
        "(logical_key, claim_seq, outcome, conflict_fields) VALUES (?, ?, ?, ?)",
        (key, claim, outcome, fields),
    )


def test_real_accepted_record_fits_the_ddl(db: sqlite3.Connection) -> None:
    identity = stage_identity()
    record = accepted_stage_from_result(identity, result_for(identity), proof("w1"))
    claim = acquire_claim(db, record.writer)
    check(claim is None, "w1 already holds the live claim for this key")
    db.execute(
        f"INSERT INTO phase1_a2_accepted_stages ({STAGE_COLUMNS}) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            record.logical_key,
            record.output.kind,
            record.output.schema_version,
            record.status.value,
            record.canonical_sha256,
            record.canonical_byte_count,
            record.semantic_data_id,
            record.stage_metadata_sha256,
            record.lineage_digest,
            record.limitations_digest,
            1,
            record.record_sha256(),
            record.record_bytes().decode(),
        ),
    )
    row = db.execute("SELECT record_json FROM phase1_a2_accepted_stages").fetchone()
    check(AcceptedStage.model_validate_json(row[0]) == record, "round trip")
    attempt(db, record.logical_key, 1, "inserted")
    attempt(db, record.logical_key, 1, "conflict", "status")


@pytest.mark.parametrize(("kind", "version"), sorted(STAGE_SCHEMAS.items()))
def test_every_approved_pair_is_accepted(db, kind: str, version: str) -> None:
    put(db, kind=kind, schema_version=version)


@pytest.mark.parametrize(
    ("kind", "version"),
    [
        ("prepared", "1"),
        ("filter_result", "1"),
        ("group_result", "1"),
        ("prepared", "3"),
        ("triage_input", "2"),
        ("a2_completion_receipt", "2"),
        ("zones", "2"),
        ("unknown", "1"),
    ],
)
def test_unapproved_or_historical_pairs_are_rejected(db, kind, version) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        put(db, kind=kind, schema_version=version)


@pytest.mark.parametrize(
    "changes",
    [
        {"logical_key": "plain"},
        {"logical_key": "a2-accepted:" + "A" * 64},
        {"logical_key": "a2-accepted:" + "g" * 64},
        {"logical_key": "a2-accepted:" + hexd("1") + "0"},
        {"logical_key": "x2-accepted:" + hexd("1")},
        {"status": "failed"},
        {"status": "COMPLETE"},
        {"canonical_sha256": "A" * 64},
        {"canonical_sha256": "a" * 63},
        {"canonical_sha256": "a" * 64 + "\n"},
        {"stage_metadata_sha256": "z" * 64},
        {"lineage_digest": b"\x00" * 64},
        {"limitations_digest": 12345},
        {"canonical_byte_count": 0},
        {"canonical_byte_count": -1},
        {"canonical_byte_count": MAX_PAYLOAD_BYTES + 1},
        {"canonical_byte_count": "10 bytes"},
        {"semantic_data_id": ""},
        {"semantic_data_id": "d" * 2049},
        {"semantic_data_id": "é" * 1100},
        {"record_json": ""},
        {"record_json": "x" * (MAX_RECORD_BYTES + 1)},
        {"record_json": b"{}"},
        {"record_sha256": None},
    ],
)
def test_check_constraints_reject_bad_rows(db, changes) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        put(db, **changes)
    check(
        db.execute("SELECT count(*) FROM phase1_a2_accepted_stages").fetchone()[0] == 0,
        "no row",
    )


def test_size_bounds_accept_the_largest_legal_values(db) -> None:
    put(
        db,
        canonical_byte_count=MAX_PAYLOAD_BYTES,
        record_json="x" * MAX_RECORD_BYTES,
        semantic_data_id="d" * 2048,
    )


def test_unique_and_foreign_keys(db) -> None:
    put(db)
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE|PRIMARY"):
        put(db, canonical_sha256=hexd("f"))
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN"):
        put(db, logical_key="a2-accepted:" + hexd("2"), writer_claim_seq=99)
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN"):
        attempt(db, key="a2-accepted:" + hexd("3"))
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN"):
        attempt(db, claim=99)
    attempt(db)
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        attempt(db)
    attempt(db, outcome="replayed")
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN"):
        db.execute("DELETE FROM phase1_a2_claims WHERE claim_seq = 1")
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN"):
        db.execute("DELETE FROM phase1_a2_accepted_stages")


@pytest.mark.parametrize(
    ("outcome", "fields"),
    [
        ("conflict", None),
        ("inserted", "status"),
        ("replayed", "status"),
        ("other", None),
        ("conflict", ""),
        ("conflict", "x" * 513),
    ],
)
def test_attempt_outcome_and_conflict_fields_agree(db, outcome, fields) -> None:
    put(db)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        attempt(db, outcome=outcome, fields=fields)


def test_claim_table_checks_and_token_storage(db) -> None:
    sql = (
        "INSERT INTO phase1_a2_claims (claim_key, execution_id, attempt_id, "
        "claim_token_sha256, state) VALUES (?, ?, ?, ?, ?)"
    )
    bad_rows = [
        ("", "e", "a", hexd("a"), "live"),
        ("x" * 2049, "e", "a", hexd("a"), "live"),
        ("k1", "", "a", hexd("a"), "live"),
        ("k2", "e", "", hexd("a"), "live"),
        ("k3", "e", "a", hexd("A"), "live"),
        ("k4", "e", "a", hexd("a"), "released!"),
        ("k5", "e", "a", hexd("a"), None),
        ("k6", "e", "a", None, "live"),
    ]
    for values in bad_rows:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(sql, values)
    columns = [row[1] for row in db.execute("PRAGMA table_info(phase1_a2_claims)")]
    check("claim_token" not in columns, "raw claim token must have no column")
    stored = db.execute("SELECT claim_token_sha256 FROM phase1_a2_claims").fetchone()
    check(stored[0] == proof("w1").claim_token_sha256, "only the digest is stored")
    check(
        "secret-1" not in str(db.execute("SELECT * FROM phase1_a2_claims").fetchall()),
        "no raw token",
    )


def test_claim_release_and_reclaim(db) -> None:
    check(acquire_claim(db, proof("w2")) is None, "live claim blocks a second attempt")
    check(release_claim(db, 1) and not release_claim(db, 1), "release once")
    second = acquire_claim(db, proof("w2"))
    check(second is not None and second > 1, f"new claim after release: {second}")
    check(second is not None and release_claim(db, second), "release again")
    with pytest.raises(A2SchemaError, match="claim-rejected"):
        acquire_claim(db, proof("w1"))


def contend(
    path: Path,
    name: str,
    key: str,
    barrier: threading.Barrier,
    outcomes: dict[str, int | None],
    errors: list[BaseException],
) -> None:
    """Acquire one claim key from a private connection after the barrier."""
    mine = connect_existing(path)
    try:
        candidate = proof(name).model_copy(update={"claim_key": key})
        barrier.wait(timeout=30)
        outcomes[name] = acquire_claim(mine, candidate)
    except BaseException as error:  # noqa: BLE001 - reported by the caller
        errors.append(error)
    finally:
        mine.close()


def test_concurrent_claim_race_has_exactly_one_winner(tmp_path: Path) -> None:
    path = build_schema5(tmp_path / "race.sqlite")
    for round_number in range(8):
        barrier = threading.Barrier(2)
        outcomes: dict[str, int | None] = {}
        errors: list[BaseException] = []
        key = f"prepare:race-{round_number}"
        threads = [
            threading.Thread(
                target=contend, args=(path, name, key, barrier, outcomes, errors)
            )
            for name in (f"x{round_number}", f"y{round_number}")
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        check(not errors, f"contender failed: {errors}")
        winners = [name for name, seq in outcomes.items() if seq is not None]
        check(len(winners) == 1 and len(outcomes) == 2, f"winners {outcomes}")
    check_db = raw(path)
    try:
        live = check_db.execute(
            "SELECT count(*), count(DISTINCT claim_key) FROM phase1_a2_claims "
            "WHERE state = 'live' AND claim_key LIKE 'prepare:race-%'"
        ).fetchone()
    finally:
        check_db.close()
    check(tuple(live) == (8, 8), f"one live row per key, got {live}")
