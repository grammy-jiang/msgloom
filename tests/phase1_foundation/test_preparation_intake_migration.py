"""Exact neutral migration and preservation tests for intake schema v4."""

import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from msgloom.contracts import ResultSchemaRegistry
from msgloom.persistence import IncompatibleSchemaError
from msgloom.persistence.models import Phase1Base
from msgloom.persistence.store import Phase1Store

V3_TABLES = {
    "phase1_schema_metadata",
    "phase1_stage_results",
    "phase1_semantic_data",
    "phase1_operation_outcomes",
    "phase1_work_claims",
    "phase1_claim_attempts",
    "phase1_reconciliations",
}
PROOF_TABLES = {
    "phase1_preparation_plan_proofs",
    "phase1_preparation_result_bindings",
}
V4_TABLES = {
    "phase1_preparation_intake_cursors",
    "phase1_preparation_intake_worksets",
    "phase1_preparation_intake_held_entries",
}


def legacy(path: Path, version: str = "3") -> None:
    """Create the exact previous table set independent of new metadata."""
    engine = create_engine(f"sqlite:///{path}")
    names = V3_TABLES - ({"phase1_reconciliations"} if version == "2" else set())
    with engine.begin() as connection:
        for name in sorted(names):
            Phase1Base.metadata.tables[name].create(connection)
        connection.exec_driver_sql(
            "INSERT INTO phase1_schema_metadata VALUES ('schema_version', ?)",
            (version,),
        )
    engine.dispose()


def snapshot(path: Path) -> tuple:
    """Capture schema and data for rollback and preservation checks."""
    with sqlite3.connect(path) as connection:
        names = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name LIKE 'phase1_%' ORDER BY name"
            )
        ]
        return tuple(
            (name, tuple(connection.execute(f"SELECT * FROM {name}").fetchall()))
            for name in names
        )


def test_new_database_has_v4_intake_tables(tmp_path: Path) -> None:
    path = tmp_path / "neutral.db"
    store = Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1())
    store.close()
    with sqlite3.connect(path) as connection:
        version = connection.execute(
            "SELECT value FROM phase1_schema_metadata WHERE key='schema_version'"
        ).fetchone()
    if (
        version != ("4",)
        or {name for name, _ in snapshot(path)} != V3_TABLES | V4_TABLES | PROOF_TABLES
    ):
        pytest.fail("Fresh neutral database did not create exact intake schema v4")


@pytest.mark.parametrize("version", ["2", "3"])
def test_exact_legacy_schema_migrates_preserving_every_row(
    tmp_path: Path, version: str
) -> None:
    path = tmp_path / "legacy.db"
    legacy(path, version)
    with sqlite3.connect(path) as connection:
        # Values are storage sentinels, not accepted semantic test inputs.
        for name in sorted(V3_TABLES - {"phase1_schema_metadata"}):
            if version == "2" and name == "phase1_reconciliations":
                continue
            columns = connection.execute(f"PRAGMA table_info({name})").fetchall()
            values = [
                b"preserved"
                if column[2] == "BLOB"
                else 1
                if column[2] in {"INTEGER", "BOOLEAN"}
                else f"sentinel-{column[1]}"
                for column in columns
            ]
            placeholders = ",".join("?" for _ in values)
            connection.execute(f"INSERT INTO {name} VALUES ({placeholders})", values)
    before = dict(snapshot(path))
    store = Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1())
    store.close()
    after = dict(snapshot(path))
    for name, rows in before.items():
        if name != "phase1_schema_metadata" and after[name] != rows:
            pytest.fail(f"Migration changed old rows in {name}")
    if dict(after["phase1_schema_metadata"]) != {
        "schema_version": "4",
        "preparation_proof_revision": "1",
    }:
        pytest.fail("Explicit migration chain did not reach v4")
    if set(after) != V3_TABLES | V4_TABLES | PROOF_TABLES:
        pytest.fail("Explicit chain omitted a schema table")


@pytest.mark.parametrize(
    "mutation",
    [
        "partial",
        "unknown_table",
        "unknown_version",
        "v2_with_v3_tables",
        "partial_v4",
        "missing_metadata",
    ],
)
def test_malformed_schema_fails_closed(tmp_path: Path, mutation: str) -> None:
    path = tmp_path / "malformed.db"
    legacy(path)
    with sqlite3.connect(path) as connection:
        if mutation == "partial":
            connection.execute("DROP TABLE phase1_stage_results")
        elif mutation == "unknown_table":
            connection.execute("CREATE TABLE phase1_unreviewed (value TEXT)")
        elif mutation == "partial_v4":
            connection.execute(
                "CREATE TABLE phase1_preparation_intake_cursors (value TEXT)"
            )
        elif mutation == "missing_metadata":
            connection.execute("DROP TABLE phase1_schema_metadata")
        else:
            version = "2" if mutation == "v2_with_v3_tables" else "999"
            connection.execute("UPDATE phase1_schema_metadata SET value=?", (version,))
    before = snapshot(path)
    with pytest.raises(IncompatibleSchemaError):
        Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1())
    if snapshot(path) != before:
        pytest.fail("Rejected migration partially modified durable rows")


# Frozen from candidate 8dfad67; independent of revised owner metadata.
OLD_V4_DDL = """
CREATE TABLE phase1_claim_attempts (
	claim_token VARCHAR NOT NULL,
	claim_key VARCHAR NOT NULL,
	claim_kind VARCHAR NOT NULL,
	execution_id VARCHAR NOT NULL,
	attempt_id VARCHAR NOT NULL,
	started_at VARCHAR NOT NULL,
	finished_at VARCHAR,
	terminal_status VARCHAR,
	external_effect VARCHAR NOT NULL,
	PRIMARY KEY (claim_token)
);
CREATE INDEX ix_phase1_claim_attempts_claim_key ON phase1_claim_attempts (claim_key);
CREATE TABLE phase1_operation_outcomes (
	execution_id VARCHAR NOT NULL,
	capability VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	result_refs TEXT NOT NULL,
	limitations TEXT NOT NULL,
	failures TEXT NOT NULL,
	external_effect VARCHAR NOT NULL,
	PRIMARY KEY (execution_id)
);
CREATE TABLE phase1_preparation_intake_cursors (
	catalog_identity VARCHAR NOT NULL,
	source_id VARCHAR NOT NULL,
	stream VARCHAR NOT NULL,
	consumer_id VARCHAR NOT NULL,
	last_release_entry_seq INTEGER NOT NULL,
	last_release_entry_digest VARCHAR(64) NOT NULL,
	PRIMARY KEY (catalog_identity, source_id, stream, consumer_id),
	CHECK (last_release_entry_seq > 0)
);
CREATE TABLE phase1_preparation_intake_held_entries (
	result_id VARCHAR NOT NULL,
	release_entry_seq INTEGER NOT NULL,
	scope_key VARCHAR NOT NULL,
	entry_digest VARCHAR(64) NOT NULL,
	reason VARCHAR NOT NULL,
	PRIMARY KEY (result_id, release_entry_seq),
	UNIQUE (scope_key, release_entry_seq)
);
CREATE INDEX phase1_intake_held ON phase1_preparation_intake_held_entries (scope_key, release_entry_seq);
CREATE TABLE phase1_preparation_intake_worksets (
	result_id VARCHAR NOT NULL,
	scope_key VARCHAR NOT NULL,
	cutoff_release_entry_seq INTEGER NOT NULL,
	cutoff_release_entry_digest VARCHAR(64) NOT NULL,
	state VARCHAR NOT NULL,
	terminal_status VARCHAR,
	result_refs TEXT NOT NULL,
	terminal_claim_token VARCHAR,
	terminal_execution_id VARCHAR,
	terminal_attempt_id VARCHAR,
	PRIMARY KEY (result_id),
	UNIQUE (scope_key, cutoff_release_entry_seq),
	CHECK (state IN ('pending', 'terminal'))
);
CREATE INDEX phase1_intake_pending ON phase1_preparation_intake_worksets (scope_key, state, cutoff_release_entry_seq);
CREATE TABLE phase1_reconciliations (
	reconciliation_id VARCHAR NOT NULL,
	claim_token VARCHAR NOT NULL,
	claim_key VARCHAR NOT NULL,
	claim_kind VARCHAR NOT NULL,
	execution_id VARCHAR NOT NULL,
	attempt_id VARCHAR NOT NULL,
	decision VARCHAR NOT NULL,
	evidence_refs TEXT NOT NULL,
	resolved_at VARCHAR NOT NULL,
	PRIMARY KEY (reconciliation_id)
);
CREATE INDEX ix_phase1_reconciliations_claim_key ON phase1_reconciliations (claim_key);
CREATE INDEX ix_phase1_reconciliations_claim_token ON phase1_reconciliations (claim_token);
CREATE TABLE phase1_schema_metadata (
	"key" VARCHAR NOT NULL,
	value VARCHAR NOT NULL,
	PRIMARY KEY ("key")
);
CREATE TABLE phase1_semantic_data (
	data_id VARCHAR NOT NULL,
	kind VARCHAR NOT NULL,
	schema_version VARCHAR NOT NULL,
	sha256 VARCHAR(64) NOT NULL,
	byte_count INTEGER NOT NULL,
	payload BLOB NOT NULL,
	PRIMARY KEY (data_id)
);
CREATE TABLE phase1_stage_results (
	result_id VARCHAR NOT NULL,
	kind VARCHAR NOT NULL,
	schema_version VARCHAR NOT NULL,
	execution_id VARCHAR NOT NULL,
	attempt_id VARCHAR NOT NULL,
	status VARCHAR NOT NULL,
	acceptable BOOLEAN NOT NULL,
	input_refs TEXT NOT NULL,
	source_versions TEXT NOT NULL,
	prepared_versions TEXT NOT NULL,
	topic_versions TEXT NOT NULL,
	configuration_version VARCHAR NOT NULL,
	code_version VARCHAR NOT NULL,
	rule_version VARCHAR,
	prompt_version VARCHAR,
	model_identifier VARCHAR,
	working_context_version TEXT,
	semantic_data_ref TEXT,
	exposed_output_ref TEXT,
	exposed_diagnostics TEXT NOT NULL,
	limitations TEXT NOT NULL,
	failures TEXT NOT NULL,
	PRIMARY KEY (result_id)
);
CREATE INDEX ix_phase1_stage_results_execution_id ON phase1_stage_results (execution_id);
CREATE INDEX ix_phase1_stage_results_kind ON phase1_stage_results (kind);
CREATE TABLE phase1_work_claims (
	claim_key VARCHAR NOT NULL,
	claim_token VARCHAR NOT NULL,
	claim_kind VARCHAR NOT NULL,
	execution_id VARCHAR NOT NULL,
	attempt_id VARCHAR NOT NULL,
	required_inputs TEXT NOT NULL,
	claimed_at VARCHAR NOT NULL,
	expires_at VARCHAR NOT NULL,
	external_effect VARCHAR NOT NULL,
	PRIMARY KEY (claim_key),
	UNIQUE (claim_token)
);
"""


def old_v4(path):
    """Create exact candidate DDL, including immutable historical metadata."""
    with sqlite3.connect(path) as connection:
        connection.executescript(OLD_V4_DDL)
        connection.execute(
            "INSERT INTO phase1_schema_metadata VALUES ('schema_version', '4')"
        )


def test_old_candidate_v4_adds_revision_without_binding_legacy_results(tmp_path):
    from tests.phase1_foundation import intake_completion_helpers as c
    from tests.phase1_foundation import intake_helpers as h

    path = tmp_path / "old.db"
    store = h.store(path)
    value, saved, owner, selections = c.admit(store)
    outcome = c.replay(store, owner, selections)
    store.close()
    with sqlite3.connect(path) as connection:
        for name in (
            "phase1_preparation_result_bindings",
            "phase1_preparation_plan_proofs",
        ):
            connection.execute(f"DROP TABLE IF EXISTS {name}")
        connection.execute(
            "DELETE FROM phase1_schema_metadata WHERE key != 'schema_version'"
        )
    before = dict(snapshot(path))
    store = h.store(path)
    if store.get_result(selections[0].result_id) != selections[0]:
        pytest.fail("Legacy selection is not readable")
    from msgloom.persistence import DependencyNotReadyError

    with pytest.raises(DependencyNotReadyError):
        store.finalize_preparation_intake_workset(
            saved.result_id,
            outcome.status,
            outcome.result_refs,
            claim=owner,
        )
    after = dict(snapshot(path))
    if any(
        after[name] != rows
        for name, rows in before.items()
        if name != "phase1_schema_metadata"
    ):
        pytest.fail("Old-candidate migration altered existing rows")
    if after["phase1_preparation_result_bindings"]:
        pytest.fail("Migration invented historical output bindings")
    fresh = c.replay(
        store,
        owner,
        selections,
        attempt="fresh-replay-attempt",
    )
    store.finalize_preparation_intake_workset(
        saved.result_id,
        fresh.status,
        fresh.result_refs,
        claim=owner,
    )
    if store.list_preparation_intake_worksets(value.scope):
        pytest.fail("Fresh exact replay did not release old pending work")
    store.close()


def test_unverified_legacy_terminal_is_visible_as_recovery_hold(tmp_path):
    from msgloom.persistence import DependencyNotReadyError
    from tests.phase1_foundation import intake_completion_helpers as c
    from tests.phase1_foundation import intake_helpers as h

    path = tmp_path / "old.db"
    store = h.store(path)
    value, saved, owner, selections = c.admit(store)
    outcome = c.replay(store, owner, selections)
    store.finalize_preparation_intake_workset(
        saved.result_id,
        outcome.status,
        outcome.result_refs,
        claim=owner,
    )
    store.close()
    with sqlite3.connect(path) as connection:
        for name in (
            "phase1_preparation_result_bindings",
            "phase1_preparation_plan_proofs",
        ):
            connection.execute(f"DROP TABLE IF EXISTS {name}")
        connection.execute(
            "DELETE FROM phase1_schema_metadata WHERE key != 'schema_version'"
        )
    before = dict(snapshot(path))
    store = h.store(path)
    with pytest.raises(DependencyNotReadyError, match="recovery.hold"):
        store.list_preparation_intake_worksets(value.scope)
    with pytest.raises(DependencyNotReadyError, match="recovery.hold"):
        store.list_preparation_intake_worksets(value.scope, after_seq=999)
    history = store.list_preparation_intake_worksets(value.scope, pending_only=False)
    if len(history) != 1 or history[0].state != "terminal":
        pytest.fail("Legacy terminal history was silently rewritten")
    if (
        dict(snapshot(path))["phase1_preparation_intake_worksets"]
        != (before["phase1_preparation_intake_worksets"])
    ):
        pytest.fail("Migration certified or reopened old terminal state")
    store.close()


def test_frozen_candidate_ddl_migrates_and_revised_reopen_is_read_only(tmp_path):
    from tests.phase1_foundation.test_preparation_intake_schema_structure import (
        snapshot as full_snapshot,
    )

    path = tmp_path / "candidate.db"
    old_v4(path)
    Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1()).close()
    with sqlite3.connect(path) as connection:
        metadata = dict(connection.execute("SELECT * FROM phase1_schema_metadata"))
    if metadata != {"schema_version": "4", "preparation_proof_revision": "1"}:
        pytest.fail("Frozen candidate migration omitted its explicit revision")
    before = full_snapshot(path)
    modified = path.stat().st_mtime_ns
    Phase1Store(f"sqlite:///{path}", ResultSchemaRegistry.phase1()).close()
    if full_snapshot(path) != before or path.stat().st_mtime_ns != modified:
        pytest.fail("Revised v4 reopen implicitly repaired or rewrote data")
