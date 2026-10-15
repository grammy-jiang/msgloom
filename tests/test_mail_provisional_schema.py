"""Strict additive Mail authority schema and fail-closed legacy inputs."""

import sqlite3

import pytest
from sqlalchemy import text

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from tests._mail_provisional import capture, prepare, promote
from tests.test_outlook_mail_atomic_promotion import SOURCE


@pytest.mark.parametrize("change", ["partial", "column", "index", "guard"])
def test_unknown_authority_schema_fails_without_ddl(tmp_path, change):
    database = tmp_path / "authority.db"
    if change != "partial":
        Catalog(f"sqlite:///{database}").close()
    with sqlite3.connect(database) as connection:
        if change == "partial":
            connection.execute(
                "CREATE TABLE mail_authority_observations (unknown TEXT)"
            )
        elif change == "column":
            connection.execute(
                "ALTER TABLE mail_authority_observations ADD COLUMN future TEXT"
            )
        elif change == "index":
            connection.execute("DROP INDEX mail_authority_run_scope")
        else:
            connection.execute("DROP TRIGGER mail_authority_decisions_immutable_update")
        before = connection.execute("SELECT name,sql FROM sqlite_master").fetchall()
    with pytest.raises(ValueError, match="Unknown or partial Mail authority"):
        Catalog(f"sqlite:///{database}")
    with sqlite3.connect(database) as connection:
        if (
            connection.execute("SELECT name,sql FROM sqlite_master").fetchall()
            != before
        ):
            pytest.fail("Invalid authority schema triggered partial DDL")


def test_additive_upgrade_preserves_ledger_and_old_rows(tmp_path):
    database = tmp_path / "upgrade.db"
    catalog = Catalog(f"sqlite:///{database}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        store.record_message(
            run_id="old",
            kind="discovery",
            observed_at="2026-10-01",
            message={"id": "old"},
            evidence_id=None,
        )
    finally:
        catalog.close()
    tables = (
        "mail_authority_observations",
        "mail_authority_decisions",
        "mail_projection_owners",
    )
    with sqlite3.connect(database) as connection:
        before = connection.execute("SELECT * FROM acquisition_facts").fetchall()
        identity = connection.execute(
            "SELECT * FROM acquisition_ledger_metadata"
        ).fetchall()
        for table in tables:
            connection.execute(f"DROP TABLE {table}")
    Catalog(f"sqlite:///{database}").close()
    with sqlite3.connect(database) as connection:
        if (
            connection.execute("SELECT * FROM acquisition_facts").fetchall() != before
            or connection.execute(
                "SELECT * FROM acquisition_ledger_metadata"
            ).fetchall()
            != identity
        ):
            pytest.fail("Additive initialization rewrote immutable ledger history")
        if connection.execute(
            "SELECT count(*) FROM mail_authority_observations"
        ).fetchone() != (0,):
            pytest.fail("Upgrade fabricated provisional observations")


def test_legacy_delta_projection_without_original_retention_fails_closed(tmp_path):
    catalog = Catalog(f"sqlite:///{tmp_path / 'legacy.db'}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    try:
        decision = prepare(store, "legacy")
        capture(store, "legacy", {"id": "m", "changeKey": "v1"})
        # Simulate a pre-upgrade pending fact, without inventing its projection.
        with catalog.writer_session() as session:
            session.execute(
                text("DROP TRIGGER mail_authority_observations_immutable_delete")
            )
            session.execute(text("DELETE FROM mail_authority_observations"))
        with pytest.raises(RuntimeError, match="requires reacquisition"):
            promote(store, decision)
        if store.get_message_state(message_id="m") is not None:
            pytest.fail("Legacy unknown projection was fabricated")
    finally:
        catalog.close()
