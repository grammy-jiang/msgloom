"""Mail-local binding schema rejects partial and unknown catalogs."""

import json
import sqlite3

import pytest
from test_outlook_mail_handoff_facts import setup as setup  # noqa: PLC0414

from message_ingest.catalog import Catalog


def test_partial_mail_schema_fails_before_any_ddl(tmp_path):
    """An unknown local table must not trigger partial catalog creation."""
    db = tmp_path / "partial.db"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE mail_component_captures (unknown TEXT)")
        before = con.execute("SELECT name,sql FROM sqlite_master").fetchall()
    try:
        catalog = Catalog(f"sqlite:///{db}")
    except ValueError:
        pass
    else:
        catalog.close()
        pytest.fail("Partial Mail schema was accepted and mutated")
    with sqlite3.connect(db) as con:
        after = con.execute("SELECT name,sql FROM sqlite_master").fetchall()
    if after != before:
        pytest.fail("Rejected schema performed DDL before validation")


def test_schema_reopen_and_parallel_initializers_preserve_history(tmp_path):
    """
    Independent instances serialize initialization without replacing data.
    """
    from concurrent.futures import ThreadPoolExecutor

    db = tmp_path / "catalog.db"
    url = f"sqlite:///{db}"
    first = Catalog(url)
    first.close()
    with sqlite3.connect(db) as con:
        before = con.execute("SELECT * FROM acquisition_ledger_metadata").fetchall()
        schema = con.execute(
            "SELECT name,sql FROM sqlite_master ORDER BY name"
        ).fetchall()

    def initialize():
        catalog = Catalog(url)
        catalog.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: initialize(), range(2)))
    with sqlite3.connect(db) as con:
        after = con.execute("SELECT * FROM acquisition_ledger_metadata").fetchall()
        reopened = con.execute(
            "SELECT name,sql FROM sqlite_master ORDER BY name"
        ).fetchall()
    if before != after or schema != reopened:
        pytest.fail("Idempotent initialization changed existing catalog identity")


def test_initializer_ddl_failure_rolls_back_entire_new_schema(tmp_path, monkeypatch):
    """Failing the last table cannot leave earlier additive DDL committed."""
    from sqlalchemy.engine import Connection

    original = Connection.exec_driver_sql

    def fail_last(connection, statement, *args, **kwargs):
        if "CREATE TABLE mail_inventory_members" in statement:
            raise RuntimeError("injected Mail DDL failure")
        return original(connection, statement, *args, **kwargs)

    monkeypatch.setattr(Connection, "exec_driver_sql", fail_last)
    db = tmp_path / "rollback.db"
    with pytest.raises(RuntimeError, match="injected Mail DDL failure"):
        Catalog(f"sqlite:///{db}")
    with sqlite3.connect(db) as con:
        if con.execute("SELECT name FROM sqlite_master").fetchall():
            pytest.fail("Failed initializer left partial DDL")


@pytest.mark.parametrize("change", ["column", "index", "guard"])
def test_unknown_complete_schema_is_rejected_without_mutation(tmp_path, change):
    """Pre-existing incompatible local definitions must fail before repair."""
    db = tmp_path / "unknown.db"
    Catalog(f"sqlite:///{db}").close()
    with sqlite3.connect(db) as con:
        if change == "column":
            con.execute("ALTER TABLE mail_component_captures ADD COLUMN future TEXT")
        elif change == "index":
            con.execute("DROP INDEX ix_mail_component_captures_selection_id")
        else:
            con.execute("DROP TRIGGER mail_component_captures_immutable_update")
        before = con.execute("SELECT name,sql FROM sqlite_master").fetchall()
    with pytest.raises(ValueError, match="Unknown or partial"):
        Catalog(f"sqlite:///{db}")
    with sqlite3.connect(db) as con:
        if con.execute("SELECT name,sql FROM sqlite_master").fetchall() != before:
            pytest.fail("Unknown schema rejection mutated the database")


@pytest.mark.parametrize("operation", ["UPDATE", "DELETE", "REPLACE"])
def test_all_binding_families_are_immutable(tmp_path, operation):
    """All four append-only families reject mutation and SQLite REPLACE."""
    from test_mail_inventory_bindings import page_evidence, seed_inventory

    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

    db = tmp_path / "immutable.db"
    catalog = Catalog(f"sqlite:///{db}")
    try:
        store = OutlookMailStore(catalog, source_id="source")
        body = {"id": "m", "changeKey": "v1"}
        page_evidence(store, "parent", "m", body)
        primary = store.record_message(
            run_id="r",
            message=body,
            kind="detail",
            evidence_id="parent",
            observed_at="2026-09-28T00:00:00+00:00",
            selection_id="s",
        )
        seed_inventory(
            store,
            "m",
            "s",
            primary.fact.source_state_key,
            "parent",
            [{"id": "a", "name": "original"}],
        )
    finally:
        catalog.close()
    for table in (
        "mail_component_captures",
        "mail_application_bindings",
        "mail_inventory_pages",
        "mail_inventory_members",
    ):
        with sqlite3.connect(db) as con:
            before = con.execute(f"SELECT * FROM {table}").fetchall()
            if not before:
                pytest.fail(f"Fixture did not populate {table}")
            if operation == "UPDATE":
                sql = f"UPDATE {table} SET payload=payload"
            elif operation == "DELETE":
                sql = f"DELETE FROM {table}"
            else:
                sql = f"INSERT OR REPLACE INTO {table} SELECT * FROM {table} LIMIT 1"
            with pytest.raises(sqlite3.IntegrityError, match="immutable Mail binding"):
                con.execute(sql)
            if con.execute(f"SELECT * FROM {table}").fetchall() != before:
                pytest.fail("Rejected immutable operation changed history")


def test_exact_old_catalog_adds_bindings_without_backfill_or_reader_ddl(tmp_path):
    """Migration preserves old release bytes; read-only open adds no schema."""
    import asyncio

    from test_mail_inventory_bindings import page_evidence
    from test_outlook_mail_handoff_facts import publish

    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
    from msgloom.sources.handoff_catalog import HandoffCatalog

    db = tmp_path / "legacy.db"
    catalog = Catalog(f"sqlite:///{db}")
    store = OutlookMailStore(catalog, source_id="source")
    page_evidence(store, "old", "m1", {"id": "m1", "changeKey": "A"})
    primary = store.record_message(
        run_id="old",
        message={"id": "m1", "changeKey": "A"},
        kind="detail",
        evidence_id="old",
        observed_at="2026-09-28T00:00:00+00:00",
    )
    publish(store, primary.fact, "old")
    catalog.close()
    preserved = (
        "messages",
        "message_observations",
        "acquisition_facts",
        "acquisition_ledger_metadata",
        "acquisition_release_groups",
        "acquisition_release_entries",
        "acquisition_release_entry_facts",
    )
    with sqlite3.connect(db) as con:
        before = {t: con.execute(f"SELECT * FROM {t}").fetchall() for t in preserved}
        for table in (
            "mail_component_captures",
            "mail_application_bindings",
            "mail_inventory_pages",
            "mail_inventory_members",
        ):
            con.execute(f"DROP TABLE {table}")
    Catalog(f"sqlite:///{db}").close()
    with sqlite3.connect(db) as con:
        after = {t: con.execute(f"SELECT * FROM {t}").fetchall() for t in preserved}
        schema = con.execute(
            "SELECT name,sql FROM sqlite_master ORDER BY name"
        ).fetchall()
        if con.execute("SELECT COUNT(*) FROM mail_application_bindings").fetchone()[0]:
            pytest.fail("Legacy data was guessed into new application bindings")
    if before != after:
        pytest.fail("Additive Mail migration changed original rows/releases")

    async def read():
        reader = HandoffCatalog(db)
        try:
            await reader.get_release_entry(1)
        finally:
            await reader.close()

    asyncio.run(read())
    with sqlite3.connect(db) as con:
        if (
            con.execute("SELECT name,sql FROM sqlite_master ORDER BY name").fetchall()
            != schema
        ):
            pytest.fail("Read-only source reader changed catalog schema")


def test_exact_fact_replay_preserves_single_original_manifest(setup):
    """Replaying saved bytes cannot assign two manifests to one fact."""
    from sqlalchemy import select
    from test_mail_inventory_bindings import base, make_page

    from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
        MailApplicationBinding,
    )

    store, parent = base(setup)
    first = make_page(store, parent, [], 1, inventory="first")
    original = store.record_inventory_page(first).fact
    from dataclasses import replace

    replay = replace(first, inventory_id="replay", page_id="replay")
    repeated = store.record_inventory_page(replay).fact
    if repeated.fact_id != original.fact_id:
        pytest.fail("Exact same-run evidence replay churned immutable fact")
    with store.catalog.Session() as session:
        manifests = session.scalars(
            select(MailApplicationBinding.payload).where(
                MailApplicationBinding.fact_id == original.fact_id,
            )
        ).all()
    if (
        len(
            {
                json.dumps(json.loads(value)["manifest"], sort_keys=True)
                for value in manifests
            }
        )
        != 1
    ):
        pytest.fail("One immutable fact acquired conflicting manifests")


def test_all_pages_change_semantics_and_empty_inventory_ignores_history(setup):
    """Equal last pages cannot conceal changed earlier membership."""
    from test_mail_authority_associations import T3
    from test_mail_inventory_bindings import (
        base,
        make_page,
        seed_inventory,
    )

    store, parent = base(setup)
    facts = []
    for index, first_id in enumerate(("a", "b")):
        first = make_page(
            store, parent, [{"id": first_id}], 1, terminal=False, inventory=str(index)
        )
        last = make_page(
            store, parent, [], 2, previous=first.page_id, inventory=str(index)
        )
        store.record_inventory_page(first)
        facts.append(store.record_inventory_page(last).fact)
    if facts[0].source_state_key == facts[1].source_state_key:
        pytest.fail("Inventory semantic key omitted an earlier page")
    state = store.full_binding_state(message_id="m1")
    if [a["attachment_id"] for a in state["attachments"]] != ["b"]:
        pytest.fail("Historical member contaminated reduced current inventory")
    if store.full_binding_complete(message_id="m1"):
        pytest.fail("Missing current child surface was silently complete")
    seed_inventory(store, "m1", "selected", parent, "detail-selected", [], T3)
    if not store.full_binding_complete(message_id="m1"):
        pytest.fail("Historical members poisoned valid empty inventory")
    if len(store.get_attachments(message_id="m1")) != 2:
        pytest.fail("Empty inventory deleted historical attachment rows")


def test_delayed_page_and_metadata_hold_until_exact_chain_is_complete(setup):
    """Final-page persistence alone cannot establish required membership."""
    from test_mail_inventory_bindings import (
        base,
        make_page,
        persist_members,
    )

    store, parent = base(setup)
    first = make_page(store, parent, [{"id": "a"}], 1, terminal=False, metadata=False)
    last = make_page(store, parent, [], 2, previous=first.page_id)
    pending = store.record_inventory_page(last)
    if pending.fact is not None:
        pytest.fail("Final page alone fabricated a complete inventory")
    store.record_inventory_page(first)
    if "attachments" in store.full_binding_state(message_id="m1")["surfaces"]:
        pytest.fail("Missing selected metadata did not hold inventory")
    persist_members(store, first, [{"id": "a"}])
    state = store.full_binding_state(message_id="m1")
    if [a["attachment_id"] for a in state["attachments"]] != ["a"]:
        pytest.fail("Delayed metadata did not reconcile complete inventory")


@pytest.mark.parametrize(
    "field,value",
    [
        ("resource_version", "x" * 65),
        ("resource_version", "wrong-parent"),
        ("parent_evidence_id", "missing"),
        ("message_id", "another"),
        ("selection_id", "x" * 65),
        ("inventory_id", "x" * 65),
    ],
)
def test_nonterminal_inventory_page_validates_binding_before_storage(
    setup,
    field,
    value,
):
    """An unfinished page cannot store an invalid or unbounded parent pin."""
    from dataclasses import replace

    from sqlalchemy import select
    from test_mail_inventory_bindings import base, make_page

    from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
        MailInventoryPage,
    )

    store, parent = base(setup)
    page = make_page(store, parent, [], 1, terminal=False)
    with pytest.raises(ValueError):
        store.record_inventory_page(replace(page, **{field: value}))
    with store.catalog.Session() as session:
        if session.scalar(select(MailInventoryPage.page_id)) is not None:
            pytest.fail("Invalid nonterminal binding leaked a saved page")


def test_exact_inventory_replay_after_aba_preserves_fact_and_current_binding(setup):
    """Preserve an exact fact's manifest and validate this capture."""
    from dataclasses import replace

    from sqlalchemy import select
    from test_mail_authority_associations import T1, primary
    from test_mail_inventory_bindings import base, make_page

    from message_ingest.catalog.models.microsoft.outlook._email_bindings import (
        MailApplicationBinding,
    )

    crawler, _, _ = setup
    store, parent = base(setup)
    page = make_page(store, parent, [], 1, inventory="original")
    original = store.record_inventory_page(page).fact
    primary(crawler, store, "B", "middle", T1)
    primary(crawler, store, "A", "returned", T1)
    replay = replace(
        page,
        page_id="replay",
        inventory_id="replay",
        selection_id="returned",
        parent_evidence_id="detail-returned",
    )
    repeated = store.record_inventory_page(replay).fact
    if repeated.fact_id != original.fact_id:
        pytest.fail("Exact repeated component fact lost its immutable pin")
    if "attachments" not in store.full_binding_state(message_id="m1")["surfaces"]:
        pytest.fail("Current application lost its explicitly selected inventory")
    recovered = store.record_inventory_page(
        replace(
            replay,
            page_id="recovery",
            inventory_id="recovery",
            run_id="recovery",
        )
    ).fact
    if recovered.revalidated_fact_id != original.fact_id:
        pytest.fail("Equivalent retry changed its exact original recovery pin")
    if "attachments" not in store.full_binding_state(message_id="m1")["surfaces"]:
        pytest.fail("Equivalent retry permanently blocked valid inventory")
    with store.catalog.Session() as session:
        payloads = session.scalars(
            select(MailApplicationBinding.payload).where(
                MailApplicationBinding.fact_id == original.fact_id,
            )
        ).all()
    if (
        len({json.dumps(json.loads(p)["manifest"], sort_keys=True) for p in payloads})
        != 1
    ):
        pytest.fail("Repeated exact fact changed its original provenance manifest")
