"""Additive mailbox-delta causal proof storage with strict DDL and replay guards."""

from pathlib import Path
from sqlite3 import connect
from typing import cast

import pytest
from sqlalchemy import Table, create_engine, inspect, select
from sqlalchemy.exc import DatabaseError

from message_ingest.catalog import Catalog
from message_ingest.catalog.models.microsoft.outlook.email import (
    FolderDeltaCheckpointCandidate,
    MailFolderDeltaCandidateBase,
)
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookFolderDeltaCheckpointStore,
)


def test_existing_mail_catalog_adds_only_folder_delta_proof_table(tmp_path: Path):
    db = tmp_path / "historical.sqlite3"
    url = f"sqlite:///{db}"
    catalog = Catalog(url)
    catalog.close()
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("DROP TABLE mail_folder_delta_candidate_bases")
            connection.execute(
                cast(Table, FolderDeltaCheckpointCandidate.__table__)
                .insert()
                .values(
                    source_id="source",
                    run_id="legacy",
                    delta_link="pending-opaque",
                    observed_at="2026-10-14T00:00:00+00:00",
                )
            )
        original = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    catalog = Catalog(url)
    try:
        updated = set(inspect(catalog.engine).get_table_names())
        if updated - original != {"mail_folder_delta_candidate_bases"}:
            pytest.fail("Migration changed historical folder delta tables")
        store = OutlookFolderDeltaCheckpointStore(catalog, "source")
        with pytest.raises(RuntimeError, match="causal baseline"):
            store.commit("legacy")
        with catalog.Session() as session:
            if session.scalar(select(MailFolderDeltaCandidateBase)) is not None:
                pytest.fail("Legacy pending folder delta was silently trusted")
        _, starting = store.get_delta_start()
        store.write_candidate(
            baseline_identity=starting,
            run_id="fresh",
            delta_link="fresh",
            observed_at="2026-10-14T00:00:01+00:00",
        )
        store.commit("fresh")
        if store.get_delta_link() != "fresh":
            pytest.fail("Additive Mail schema blocked fresh causal promotion")
    finally:
        catalog.close()
    Catalog(url).close()


def test_partial_folder_delta_causal_schema_fails_closed_without_ddl(tmp_path: Path):
    db = tmp_path / "partial.sqlite3"
    with connect(db) as connection:
        connection.execute("CREATE TABLE mail_folder_delta_candidate_bases (bad TEXT)")
        before = tuple(
            connection.execute(
                "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL"
            ).fetchall()
        )
    with pytest.raises(ValueError, match="causal schema"):
        Catalog(f"sqlite:///{db}")
    with connect(db) as connection:
        after = tuple(
            connection.execute(
                "SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL"
            ).fetchall()
        )
    if before != after:
        pytest.fail("Rejected partial folder causal table was modified")


def test_folder_delta_causal_proof_is_sql_immutable(tmp_path: Path):
    catalog = Catalog(f"sqlite:///{tmp_path / 'guard.db'}")
    try:
        store = OutlookFolderDeltaCheckpointStore(catalog, "source")
        _, baseline = store.get_delta_start()
        store.write_candidate(
            baseline_identity=baseline,
            run_id="run",
            delta_link="current",
            observed_at="2026-10-14T00:00:00+00:00",
        )
        with (
            pytest.raises(DatabaseError, match="immutable Mail delta causal proof"),
            catalog.writer_session() as writer,
        ):
            proof = writer.get(MailFolderDeltaCandidateBase, ("source", "run"))
            if proof is None:
                pytest.fail("Causal proof was not persisted")
            proof.baseline_identity = "p:" + "b" * 64
        with catalog.Session() as session:
            row = session.get(MailFolderDeltaCandidateBase, ("source", "run"))
            if row is None or row.baseline_identity != baseline:
                pytest.fail("SQL trigger permitted alteration of committed proof")
    finally:
        catalog.close()
