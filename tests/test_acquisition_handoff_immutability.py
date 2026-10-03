"""Reject replacement through every ledger key with recursion disabled."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from test_acquisition_handoff_catalog import (
    Stream,
    entry,
    fact,
    group,
    release,
    stage,
)
from test_acquisition_handoff_catalog import (
    catalog as _catalog,
)

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

catalog = _catalog

CONFLICTS = [
    ("acquisition_facts", "fact_id"),
    ("acquisition_facts", "staging_key"),
    ("acquisition_ledger_metadata", "singleton"),
    ("acquisition_ledger_metadata", "catalog_identity"),
    ("acquisition_release_groups", "release_group_id"),
    ("acquisition_release_entries", "release_entry_seq"),
    ("acquisition_release_entry_facts", "release_entry_seq, ordinal"),
    ("acquisition_run_outcomes", "run_id, attempt_id"),
]


def populate(catalog):
    """Create real published rows and a bounded attempt outcome."""
    first = stage(catalog, fact())
    release(catalog, group(), [entry(first)])
    with catalog.engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO acquisition_run_outcomes VALUES "
            "('run-1', 'attempt-1', 'source', 'outlook_discover', "
            "'complete', 'finished', 'complete')"
        )


@pytest.mark.parametrize("table, conflict", CONFLICTS)
@pytest.mark.parametrize("operation", ["replace", "upsert", "update"])
def test_all_immutable_keys_reject_conflicts(catalog, table, conflict, operation):
    """INSERT guards must also protect alternate unique and composite keys."""
    populate(catalog)
    with catalog.engine.connect() as connection:
        before = dict(
            connection.exec_driver_sql(f"SELECT * FROM {table}").mappings().one()
        )
    values = dict(before)
    if table == "acquisition_facts":
        alternate = "staging_key" if conflict == "fact_id" else "fact_id"
        values[alternate] = "different-key"
        values["payload"] = "{}"
    elif table == "acquisition_ledger_metadata":
        alternate = "catalog_identity" if conflict == "singleton" else "singleton"
        values[alternate] = (
            "different-catalog" if alternate == "catalog_identity" else 2
        )
    elif "payload" in values:
        values["payload"] = "{}"
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
    if operation == "replace":
        sql = sql.replace("INSERT INTO", "INSERT OR REPLACE INTO")
    elif operation == "upsert":
        column = next(iter(values))
        sql += f" ON CONFLICT ({conflict}) DO UPDATE SET {column}=excluded.{column}"
    else:
        assignments = ", ".join(f"{name}=:{name}" for name in values)
        sql = f"UPDATE OR REPLACE {table} SET {assignments}"
    with catalog.engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA recursive_triggers=0")
        if connection.exec_driver_sql("PRAGMA recursive_triggers").scalar_one() != 0:
            pytest.fail("Replacement test did not disable recursive triggers")
        with pytest.raises(DatabaseError, match="immutable"):
            connection.execute(text(sql), values)
    with catalog.engine.connect() as connection:
        after = dict(
            connection.exec_driver_sql(f"SELECT * FROM {table}").mappings().one()
        )
    if after != before:
        pytest.fail("Conflict modified an immutable ledger row")


@pytest.mark.parametrize("table, conflict", CONFLICTS)
def test_reopen_installs_missing_insert_guards(tmp_path, table, conflict):
    """Additive reopen protects an existing ledger without rewriting rows."""
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    original = Catalog(url)
    populate(original)
    identity = AcquisitionHandoffStore(original).catalog_identity()
    with original.engine.begin() as connection:
        triggers = (
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='trigger' "
                "AND sql LIKE '%BEFORE INSERT%'"
            )
            .scalars()
            .all()
        )
        for trigger in triggers:
            connection.exec_driver_sql(f'DROP TRIGGER "{trigger}"')
        original_row = dict(
            connection.exec_driver_sql(f"SELECT * FROM {table}").mappings().one()
        )
    original.close()
    reopened = Catalog(url)
    try:
        if AcquisitionHandoffStore(reopened).catalog_identity() != identity:
            pytest.fail("Reopen changed catalog identity")
        values = dict(original_row)
        if table == "acquisition_facts":
            values["staging_key" if conflict == "fact_id" else "fact_id"] = "new"
        if table == "acquisition_ledger_metadata":
            if conflict == "singleton":
                values["catalog_identity"] = "new"
            else:
                values["singleton"] = 2
        with reopened.engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA recursive_triggers=0")
            if (
                connection.exec_driver_sql("PRAGMA recursive_triggers").scalar_one()
                != 0
            ):
                pytest.fail("Reopen test did not disable recursive triggers")
            with pytest.raises(DatabaseError, match="immutable"):
                connection.execute(
                    text(
                        f"INSERT OR REPLACE INTO {table} "
                        f"({', '.join(values)}) VALUES "
                        f"({', '.join(':' + key for key in values)})"
                    ),
                    values,
                )
        store = AcquisitionHandoffStore(reopened)
        if len(store.list_release_entries("source", Stream.OUTLOOK_MAIL)) != 1:
            pytest.fail("Reopen lost the original release")
    finally:
        reopened.close()


def test_effective_index_and_distinct_composite_keys_remain_writable(catalog):
    """Fresh state and distinct attempt identities remain valid writes."""
    populate(catalog)
    latest = stage(catalog, fact(state="v2", run="run-2"))
    store = AcquisitionHandoffStore(catalog)
    with catalog.engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA recursive_triggers=0")
        state = store.current_effective_state(connection, latest.effective_key)
        if state is None or state["fact_id"] != latest.fact_id:
            pytest.fail("Immutable guards blocked a freshness-index update")
        connection.exec_driver_sql(
            "INSERT INTO acquisition_run_outcomes VALUES "
            "('run-1', 'attempt-2', 'source', 'outlook_discover', "
            "'complete', 'finished', 'complete'), "
            "('run-2', 'attempt-1', 'source', 'outlook_discover', "
            "'complete', 'finished', 'complete')"
        )
        connection.execute(
            text(
                "UPDATE acquisition_effective_states SET fact_id=:fact "
                "WHERE effective_key=:key"
            ),
            {"fact": latest.fact_id, "key": latest.effective_key.digest},
        )


@pytest.mark.parametrize(
    "table",
    [
        "acquisition_facts",
        "acquisition_release_groups",
        "acquisition_release_entry_facts",
        "acquisition_run_outcomes",
    ],
)
def test_hidden_rowid_conflict_cannot_replace_immutable_rows(catalog, table):
    """SQLite rowid conflicts cannot bypass declared-key replacement guards."""
    populate(catalog)
    with catalog.engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA recursive_triggers=0")
        if connection.exec_driver_sql("PRAGMA recursive_triggers").scalar_one() != 0:
            pytest.fail("Rowid test did not disable recursive triggers")
        values = dict(
            connection.exec_driver_sql(f"SELECT rowid, * FROM {table}").mappings().one()
        )
        if table == "acquisition_facts":
            values.update(fact_id="new-fact", staging_key="new-stage")
        elif table == "acquisition_release_groups":
            values["release_group_id"] = "new-group"
        elif table == "acquisition_release_entry_facts":
            # Remove the membership guard only to isolate replacement safety.
            connection.exec_driver_sql(
                "DROP TRIGGER IF EXISTS canonical_acquisition_entry_member"
            )
            values["ordinal"] = 1
        else:
            values["attempt_id"] = "new-attempt"
        with pytest.raises(DatabaseError, match="immutable"):
            connection.execute(
                text(
                    f"INSERT OR REPLACE INTO {table} "
                    f"({', '.join(values)}) VALUES "
                    f"({', '.join(':' + key for key in values)})"
                ),
                values,
            )
