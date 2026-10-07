"""Bind SQL membership and every public reader to canonical entry contents."""

import json
from dataclasses import replace

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

from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

catalog = _catalog

MEMBERS = "acquisition_release_entry_facts"
ENTRIES = "acquisition_release_entries"


def publish_pair(catalog, core=False):
    """Publish two ordered roles using a caller-owned Session or Connection."""
    store = AcquisitionHandoffStore(catalog)
    scope = catalog.engine.begin() if core else catalog.writer_session()
    with scope as writer:
        first = store.stage_state_fact_in_session(writer, fact())
        second = store.stage_state_fact_in_session(
            writer, fact(resource="profile-proof")
        )
        spec = replace(
            entry(first),
            facts=((first.fact_id, "primary"), (second.fact_id, "proof")),
        )
        store.release_effective_group_in_session(writer, group(), [spec])
    page = store.list_release_entries("source", Stream.OUTLOOK_MAIL)
    return page[0], first, second


def remove_guards(connection, table):
    """Model legacy corruption in an isolated test database only."""
    names = (
        connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
            (table,),
        )
        .scalars()
        .all()
    )
    for name in names:
        connection.exec_driver_sql(f'DROP TRIGGER "{name}"')


@pytest.mark.parametrize("core", [False, True])
def test_ordered_membership_publication_and_retry(catalog, core):
    """Both writer types preserve order and idempotent API retry."""
    row, first, second = publish_pair(catalog, core)
    store = AcquisitionHandoffStore(catalog)
    members = store.load_release_facts(row["release_entry_seq"])
    if [f.fact_id for f in members] != [first.fact_id, second.fact_id]:
        pytest.fail("Publication changed the canonical fact order")
    spec = replace(
        entry(first),
        facts=((first.fact_id, "primary"), (second.fact_id, "proof")),
    )
    scope = catalog.engine.begin() if core else catalog.writer_session()
    with scope as writer:
        store.release_effective_group_in_session(writer, group(), [spec])
    if len(store.list_release_entries("source", Stream.OUTLOOK_MAIL)) != 1:
        pytest.fail("Retry republished an immutable entry")


@pytest.mark.parametrize("ordinal", [-1, 1, 128, 0.5])
def test_post_publication_membership_insert_rejected(catalog, ordinal):
    """Core cannot append a member absent from the immutable entry payload."""
    first = stage(catalog, fact())
    other = stage(catalog, fact(resource="unrelated"))
    release(catalog, group(), [entry(first)])
    with pytest.raises(DatabaseError), catalog.engine.begin() as connection:
        connection.execute(
            text(
                f"INSERT INTO {MEMBERS} "
                "(release_entry_seq, ordinal, fact_id, role) "
                "VALUES (1, :ordinal, :fact, 'primary')"
            ),
            {"ordinal": ordinal, "fact": other.fact_id},
        )
    with catalog.engine.connect() as connection:
        rows = connection.exec_driver_sql(
            f"SELECT ordinal, fact_id, role FROM {MEMBERS}"
        ).all()
    if rows != [(0, first.fact_id, "primary")]:
        pytest.fail("Rejected insert altered membership")


@pytest.mark.parametrize("bad", ["fact", "role"])
def test_membership_insert_must_match_canonical_pair(catalog, bad):
    """Even an empty canonical slot cannot accept another fact or role."""
    row, first, second = publish_pair(catalog)
    with catalog.engine.begin() as connection:
        connection.exec_driver_sql(f"DROP TRIGGER immutable_{MEMBERS}_DELETE")
        connection.exec_driver_sql(f"DELETE FROM {MEMBERS} WHERE ordinal=0")
    with pytest.raises(DatabaseError), catalog.engine.begin() as connection:
        connection.execute(
            text(f"INSERT INTO {MEMBERS} VALUES (:seq, 0, :fact, :role)"),
            {
                "seq": row["release_entry_seq"],
                "fact": second.fact_id if bad == "fact" else first.fact_id,
                "role": "proof" if bad == "role" else "primary",
            },
        )


@pytest.mark.parametrize(
    "corruption", ["missing", "extra", "reordered", "role", "fact", "payload", "digest"]
)
@pytest.mark.parametrize("reader", ["page", "entry", "facts"])
def test_readers_reject_corrupt_legacy_membership(catalog, corruption, reader):
    """No public reader may silently hide or admit inconsistent legacy rows."""
    row, first, second = publish_pair(catalog)
    seq = row["release_entry_seq"]
    with catalog.engine.begin() as connection:
        remove_guards(connection, MEMBERS)
        remove_guards(connection, ENTRIES)
        if corruption == "missing":
            connection.exec_driver_sql(f"DELETE FROM {MEMBERS} WHERE ordinal=1")
        elif corruption == "extra":
            connection.execute(
                text(f"INSERT INTO {MEMBERS} VALUES (:seq, 2, :fact, 'proof')"),
                {"seq": seq, "fact": first.fact_id},
            )
        elif corruption == "reordered":
            connection.execute(
                text(
                    f"UPDATE {MEMBERS} SET fact_id=CASE ordinal "
                    "WHEN 0 THEN :second ELSE :first END, "
                    "role=CASE ordinal WHEN 0 THEN 'proof' ELSE 'primary' END"
                ),
                {"first": first.fact_id, "second": second.fact_id},
            )
        elif corruption == "role":
            connection.exec_driver_sql(
                f"UPDATE {MEMBERS} SET role='context' WHERE ordinal=0"
            )
        elif corruption == "fact":
            connection.execute(
                text(f"UPDATE {MEMBERS} SET fact_id=:fact WHERE ordinal=0"),
                {"fact": second.fact_id},
            )
        elif corruption == "payload":
            payload = json.loads(row["payload"])
            payload["resource_identity"] = "forged"
            connection.execute(
                text(f"UPDATE {ENTRIES} SET payload=:payload"),
                {"payload": json.dumps(payload)},
            )
        else:
            connection.exec_driver_sql(f"UPDATE {ENTRIES} SET entry_digest='wrong'")
    store = AcquisitionHandoffStore(catalog)
    with pytest.raises(ValueError, match="membership|digest|payload"):
        if reader == "page":
            store.list_release_entries("source", Stream.OUTLOOK_MAIL)
        elif reader == "entry":
            store.load_release_entry(seq)
        else:
            store.load_release_facts(seq)
