"""Keep reviewed identity comparisons BINARY before schema migration."""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event

from msgloom.contracts import ExternalEffectState, TerminalStatus
from msgloom.persistence import IncompatibleSchemaError
from msgloom.persistence.schema_store import initialize_schema
from tests.phase1_foundation import intake_helpers as h
from tests.phase1_foundation.test_preparation_intake_migration import old_v4
from tests.phase1_foundation.test_preparation_intake_schema_structure import (
    database,
    rebuild,
    snapshot,
)

VERSIONS = ("2", "3", "old4", "4")
RESULTS = "phase1_stage_results"
CURSORS = "phase1_preparation_intake_cursors"


def fixture(path: Path, version: str) -> None:
    """Create one supported schema with preserved storage sentinels."""
    if version == "old4":
        old_v4(path)
    else:
        database(path, version)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO phase1_schema_metadata VALUES ('sentinel', 'retained')"
        )
        columns = connection.execute(f"PRAGMA table_info({RESULTS})").fetchall()
        values = [
            1 if column[2] == "BOOLEAN" else f"sentinel-{column[1]}"
            for column in columns
        ]
        parameters = ",".join("?" for _ in values)
        connection.execute(f"INSERT INTO {RESULTS} VALUES ({parameters})", values)


def require_rejected_unchanged(path: Path) -> None:
    """Require refusal before persistent DDL, retaining rows and file state."""
    before = snapshot(path), path.stat().st_mtime_ns
    engine = create_engine(f"sqlite:///{path}", connect_args={"autocommit": True})
    writes = []

    def record(_connection, _cursor, statement, _params, _context, _many):
        if (
            statement.lstrip()
            .upper()
            .startswith(
                ("CREATE", "ALTER", "DROP", "INSERT", "UPDATE", "DELETE", "REPLACE")
            )
        ):
            writes.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    rejected = False
    try:
        try:
            initialize_schema(engine)
        except IncompatibleSchemaError:
            rejected = True
    finally:
        engine.dispose()
    unchanged = (snapshot(path), path.stat().st_mtime_ns) == before
    if not rejected or writes or not unchanged:
        pytest.fail(
            f"Malformed collation: rejected={rejected}, "
            f"persistent_writes={len(writes)}, unchanged={unchanged}"
        )


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("collation", ["NOCASE", "RTRIM"])
@pytest.mark.parametrize(
    "location",
    ["column", "masked_column", "unindexed_column", "primary", "unique", "index"],
)
def test_nonbinary_semantics_fail_before_any_migration(
    tmp_path, version, collation, location
):
    path = tmp_path / "neutral.db"
    fixture(path, version)
    with sqlite3.connect(path) as connection:
        if location == "index":
            connection.execute("DROP INDEX ix_phase1_stage_results_execution_id")
            connection.execute(
                f"CREATE INDEX ix_phase1_stage_results_execution_id ON {RESULTS} "
                f"(execution_id COLLATE {collation})"
            )
        else:
            table = "phase1_work_claims" if location == "unique" else RESULTS

            def change(sql):
                if location == "unique":
                    return sql.replace(
                        "UNIQUE (claim_token)",
                        f"UNIQUE (claim_token COLLATE {collation})",
                    )
                if location == "primary":
                    return sql.replace(
                        "PRIMARY KEY (result_id)",
                        f"PRIMARY KEY (result_id COLLATE {collation})",
                    )
                column = "attempt_id" if location == "unindexed_column" else "result_id"
                changed = sql.replace(
                    f"{column} VARCHAR NOT NULL",
                    f'"{column}" VARCHAR COLLATE "{collation}" NOT NULL',
                )
                if location == "masked_column":
                    changed = changed.replace(
                        "PRIMARY KEY (result_id)",
                        "PRIMARY KEY (result_id COLLATE BINARY)",
                    )
                return changed

            rebuild(connection, table, change)
    require_rejected_unchanged(path)


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize("location", ["primary", "index"])
def test_descending_key_semantics_are_not_the_reviewed_indexes(
    tmp_path, version, location
):
    path = tmp_path / "neutral.db"
    fixture(path, version)
    with sqlite3.connect(path) as connection:
        if location == "index":
            connection.execute("DROP INDEX ix_phase1_stage_results_execution_id")
            connection.execute(
                f"CREATE INDEX ix_phase1_stage_results_execution_id ON {RESULTS} "
                "(execution_id DESC)"
            )
        else:
            rebuild(
                connection,
                RESULTS,
                lambda sql: sql.replace(
                    "PRIMARY KEY (result_id)", "PRIMARY KEY (result_id DESC)"
                ),
            )
    require_rejected_unchanged(path)


@pytest.mark.parametrize("version", ["old4", "4"])
@pytest.mark.parametrize("collation", ["NOCASE", "RTRIM"])
def test_cursor_consumer_collation_is_validated_before_open(
    tmp_path, version, collation
):
    path = tmp_path / "neutral.db"
    fixture(path, version)
    with sqlite3.connect(path) as connection:
        rebuild(
            connection,
            CURSORS,
            lambda sql: sql.replace(
                "consumer_id VARCHAR NOT NULL",
                f"consumer_id VARCHAR COLLATE {collation} NOT NULL",
            ),
        )
    require_rejected_unchanged(path)


@pytest.mark.parametrize(
    "table,column",
    [
        ("phase1_preparation_plan_proofs", "claim_token"),
        ("phase1_preparation_plan_proofs", "claim_key"),
        ("phase1_preparation_result_bindings", "result_id"),
        ("phase1_preparation_result_bindings", "claim_token"),
    ],
)
def test_proof_identities_keep_exact_binary_comparisons(tmp_path, table, column):
    path = tmp_path / "neutral.db"
    fixture(path, "4")
    with sqlite3.connect(path) as connection:
        rebuild(
            connection,
            table,
            lambda sql: sql.replace(
                f"{column} VARCHAR NOT NULL",
                f"{column} VARCHAR COLLATE NOCASE NOT NULL",
            ),
        )
    require_rejected_unchanged(path)


@pytest.mark.parametrize("version", VERSIONS)
def test_equivalent_explicit_binary_ddl_remains_supported(tmp_path, version):
    path = tmp_path / "neutral.db"
    fixture(path, version)
    with sqlite3.connect(path) as connection:
        rebuild(
            connection,
            RESULTS,
            lambda sql: sql.replace(
                "result_id VARCHAR NOT NULL",
                '"result_id" VARCHAR /* COLLATE NOCASE */ COLLATE "BiNaRy" NOT NULL',
            ),
        )
    before_rows = dict(snapshot(path)[1])[RESULTS]
    h.store(path).close()
    if dict(snapshot(path)[1])[RESULTS] != before_rows:
        pytest.fail("Equivalent BINARY migration changed saved results")
    before = snapshot(path), path.stat().st_mtime_ns
    h.store(path).close()
    if (snapshot(path), path.stat().st_mtime_ns) != before:
        pytest.fail("Validated revised schema reopen performed a write")


@pytest.mark.parametrize("version", VERSIONS)
def test_case_distinct_consumers_keep_separate_claims_cursors_and_pending(
    tmp_path, version
):
    path = tmp_path / "neutral.db"
    fixture(path, version)
    upper = h.workset(target=h.scope(consumer="Daily"))
    lower = h.workset(target=h.scope(consumer="daily"), seq=9)
    store = h.store(path)
    try:
        upper_claim = h.claim(store, upper, identity="upper")
        lower_claim = h.claim(store, lower, identity="lower")
        if upper_claim.claim_key == lower_claim.claim_key:
            pytest.fail("Case-distinct consumers shared a claim key")
        store.finalize_preparation_intake(
            h.result(store, upper, upper_claim, "upper"), upper, claim=upper_claim
        )
        if store.get_preparation_intake_cursor(lower.scope) != lower.previous:
            pytest.fail("Unadmitted consumer inherited another consumer cursor")
        if store.list_preparation_intake_worksets(lower.scope):
            pytest.fail("Unadmitted consumer inherited pending work")
        store.finish_claim(
            upper_claim, TerminalStatus.COMPLETE, ExternalEffectState.NONE
        )
        store.finalize_preparation_intake(
            h.result(store, lower, lower_claim, "lower"), lower, claim=lower_claim
        )
        store.finish_claim(
            lower_claim, TerminalStatus.COMPLETE, ExternalEffectState.NONE
        )
    finally:
        store.close()
    store = h.store(path)
    try:
        for value, identity in [(upper, "upper"), (lower, "lower")]:
            if store.get_preparation_intake_cursor(value.scope) != value.cutoff:
                pytest.fail("Consumer cursor changed across independent admission")
            pending = store.list_preparation_intake_worksets(value.scope)
            if len(pending) != 1 or pending[0].workset.result_id != identity:
                pytest.fail("Pending work crossed consumer identity boundaries")
    finally:
        store.close()
