"""Additive, fail-closed Mail cursor causal-proof schema migration."""

from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import Table, create_engine, inspect, select
from sqlalchemy.exc import DatabaseError

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.microsoft.outlook.email import (
    DeltaCheckpoint,
    DeltaCheckpointCandidate,
    MailDeltaCandidateBase,
)
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)


def test_historical_catalog_gain_additive_proof_table_without_backfill(
    tmp_path: Path,
) -> None:
    path = tmp_path / "historical.db"
    url = f"sqlite:///{path}"
    # Initialize all historically supported Mail tables using their real SQL
    # guards, then remove ONLY the new additive causal table. The remaining
    # DDL is an exact pre-upgrade catalog, not hand-built ORM assumptions.
    created = Catalog(url)
    created.close()
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE mail_delta_candidate_bases")
            connection.exec_driver_sql("DROP TABLE mail_folder_delta_candidate_bases")
            connection.exec_driver_sql("DROP TABLE mail_delta_absence_generations")
            connection.execute(
                cast(Table, DeltaCheckpoint.__table__)
                .insert()
                .values(
                    source_id="source",
                    folder_id="inbox",
                    delta_link="legacy-X",
                    committed_at="2026-10-01T00:00:00+00:00",
                    run_id="older",
                )
            )
            connection.execute(
                cast(Table, DeltaCheckpointCandidate.__table__)
                .insert()
                .values(
                    source_id="source",
                    folder_id="inbox",
                    run_id="pending-legacy",
                    delta_link="pending-Y",
                    observed_at="2026-10-02T00:00:00+00:00",
                )
            )
        old_names = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    catalog = Catalog(url)
    try:
        new_names = set(inspect(catalog.engine).get_table_names())
        if new_names - old_names != {
            "mail_delta_candidate_bases",
            "mail_folder_delta_candidate_bases",
            "mail_delta_absence_generations",
        }:
            pytest.fail("Mail proof migration altered historical tables")
        store = OutlookDeltaCheckpointStore(catalog, "source")
        if store.get_delta_link("inbox") != "legacy-X":
            pytest.fail("Mail proof migration rewrote committed Graph history")
        with catalog.Session() as session:
            proof = session.scalar(select(MailDeltaCandidateBase))
            pending = session.scalar(
                select(DeltaCheckpointCandidate).filter_by(
                    run_id="pending-legacy",
                    source_id="source",
                    folder_id="inbox",
                )
            )
        if proof is not None or pending is None:
            pytest.fail("Legacy candidate was fabricated or erased")
        with pytest.raises(RuntimeError, match="causal baseline"):
            store.commit("pending-legacy")
        _, identity = store.get_delta_start("inbox")
        store.write_candidate(
            baseline_identity=identity,
            run_id="fresh",
            folder_id="inbox",
            delta_link="fresh-Z",
            observed_at="2026-10-03T00:00:00+00:00",
        )
        store.commit("fresh")
        if store.get_delta_link("inbox") != "fresh-Z":
            pytest.fail("Legacy catalog did not admit new causally bound runs")
    finally:
        catalog.close()
    reopened = Catalog(url)
    reopened.close()


def test_causal_schema_can_add_absence_epoch_to_existing_proof_table(
    tmp_path: Path,
) -> None:
    """An already valid proof schema may add the epoch without DDL rewrites."""
    database = tmp_path / "proof_only.db"
    url = f"sqlite:///{database}"
    catalog = Catalog(url)
    catalog.close()
    with create_engine(url).begin() as connection:
        before_proof = connection.exec_driver_sql(
            "SELECT name,sql FROM sqlite_master "
            "WHERE tbl_name='mail_delta_candidate_bases' AND sql IS NOT NULL"
        ).all()
        connection.exec_driver_sql("DROP TABLE mail_delta_absence_generations")
    catalog = Catalog(url)
    try:
        with catalog.engine.connect() as connection:
            after_proof = connection.exec_driver_sql(
                "SELECT name,sql FROM sqlite_master "
                "WHERE tbl_name='mail_delta_candidate_bases' AND sql IS NOT NULL"
            ).all()
        if (
            before_proof != after_proof
            or "mail_delta_absence_generations"
            not in inspect(catalog.engine).get_table_names()
        ):
            pytest.fail("Additive epoch upgrade rewrote immutable proof table")
    finally:
        catalog.close()


def test_incompatible_or_partial_causal_schema_rejected_without_changes(
    tmp_path: Path,
) -> None:
    from sqlite3 import connect

    path = tmp_path / "malformed.db"
    with connect(path) as connection:
        connection.execute("CREATE TABLE mail_delta_candidate_bases (bad TEXT)")
        before = tuple(
            connection.execute(
                "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL"
            ).fetchall()
        )
    with pytest.raises(ValueError, match="causal schema"):
        Catalog(f"sqlite:///{path}")
    with connect(path) as connection:
        after = tuple(
            connection.execute(
                "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL"
            ).fetchall()
        )
    if before != after:
        pytest.fail("Rejected incompatible causal table changed the catalog")


def test_causal_proof_immutable_to_sql_mutation(tmp_path: Path) -> None:
    catalog = Catalog(f"sqlite:///{tmp_path / 'proof.db'}")
    try:
        store = OutlookDeltaCheckpointStore(catalog, "source")
        _, baseline = store.get_delta_start("inbox")
        store.write_candidate(
            baseline_identity=baseline,
            run_id="run",
            folder_id="inbox",
            delta_link="Y",
            observed_at="2026-10-03T00:00:00+00:00",
        )
        with (
            pytest.raises(DatabaseError, match="immutable Mail delta causal proof"),
            catalog.writer_session() as writer,
        ):
            row = writer.get(MailDeltaCandidateBase, ("source", "run", "inbox"))
            if row is None:
                pytest.fail("Persisted causal proof missing")
            row.baseline_identity = "p:" + "a" * 64
        with catalog.Session() as session:
            value = session.get(MailDeltaCandidateBase, ("source", "run", "inbox"))
            if value is None or value.baseline_identity != baseline:
                pytest.fail("Database update guard allowed proof mutation")
    finally:
        catalog.close()
