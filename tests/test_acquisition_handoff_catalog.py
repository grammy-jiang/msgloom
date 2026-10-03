"""Exercise atomic fact staging and immutable, freshness-gated publication."""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DatabaseError

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind as Kind,
)
from message_ingest.acquisition.handoff import (
    AcquisitionStream as Stream,
)
from message_ingest.acquisition.handoff import (
    FactSpec,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    SourceVersionLocator,
    source_state_key,
)
from message_ingest.acquisition.handoff import (
    StorageRelation as Relation,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore


@pytest.fixture
def catalog(tmp_path):
    value = Catalog(f"sqlite:///{tmp_path / 'a1.db'}")
    yield value
    value.close()


def fact(resource="message-1", state="v1", run="run-1", **kw):
    return FactSpec(
        source_id="source",
        stream=Stream.OUTLOOK_MAIL,
        run_id=run,
        spider_name="outlook_discover",
        fact_kind=Kind.RESOURCE_OBSERVATION,
        resource_kind="message",
        resource_identity=resource,
        provider_observed_at="2026-10-03T00:00:00Z",
        source_state_key=source_state_key({"changeKey": state}),
        source_version_locator=SourceVersionLocator(
            kind="evidence",
            evidence_id=f"evidence-{state}",
            resource_identity=resource,
        ),
        **kw,
    )


def group(run="run-1", subject="mailbox"):
    return ReleaseGroupSpec(
        source_id="source",
        stream=Stream.OUTLOOK_MAIL,
        release_kind=ReleaseKind.RESOURCE_SET,
        subject_kind="mailbox",
        subject_identity=subject,
        owner_run_id=run,
        released_at="2026-10-03T01:00:00Z",
        coverage_kind="complete",
    )


def entry(f):
    return ReleaseEntrySpec(
        resource_kind=f.resource_kind,
        resource_identity=f.resource_identity,
        facts=((f.fact_id, "primary"),),
    )


def stage(catalog, spec):
    store = AcquisitionHandoffStore(catalog)
    with catalog.writer_session() as session:
        return store.stage_state_fact_in_session(session, spec)


def release(catalog, spec, entries):
    store = AcquisitionHandoffStore(catalog)
    with catalog.writer_session() as session:
        return store.release_effective_group_in_session(session, spec, entries)


def test_identity_survives_reopen_and_copy(tmp_path: Path):
    path = tmp_path / "first.db"
    first = Catalog(f"sqlite:///{path}")
    identity = AcquisitionHandoffStore(first).catalog_identity()
    first.close()
    copied = tmp_path / "copied.db"
    shutil.copyfile(path, copied)
    for target in (path, copied):
        reopened = Catalog(f"sqlite:///{target}")
        try:
            if AcquisitionHandoffStore(reopened).catalog_identity() != identity:
                pytest.fail("Catalog identity changed on reopen/backup")
        finally:
            reopened.close()


def test_fact_idempotence_and_equivalence(catalog):
    first = stage(catalog, fact())
    repeated = stage(catalog, fact())
    equivalent = stage(catalog, fact(run="run-2"))
    if first != repeated or first.storage_relation != Relation.ADVANCED:
        pytest.fail("Exact staging must reuse the original immutable fact")
    if equivalent.storage_relation != Relation.CURRENT_EQUIVALENT:
        pytest.fail("Same semantic state must be equivalent")
    store = AcquisitionHandoffStore(catalog)
    with catalog.Session() as session:
        effective = store.current_effective_state(session, first.effective_key)
    if effective is None or effective["fact_id"] != first.fact_id:
        pytest.fail("Equivalent observation replaced effective fact")


def test_stale_and_authority_staged_cannot_replace_effective(catalog):
    winner = stage(catalog, fact())
    stale = stage(catalog, fact(state="old", storage_relation=Relation.STALE))
    store = AcquisitionHandoffStore(catalog)
    with catalog.writer_session() as session:
        staged = store.stage_authority_fact_in_session(session, fact(state="next"))
        current = store.current_effective_state(session, winner.effective_key)
    if current is None or current["fact_id"] != winner.fact_id:
        pytest.fail("Non-effective observation changed the winning state")
    release(
        catalog,
        group(),
        [
            replace(
                entry(stale),
                facts=(
                    (stale.fact_id, "primary"),
                    (staged.fact_id, "proof"),
                ),
            )
        ],
    )
    if store.list_release_entries("source", Stream.OUTLOOK_MAIL):
        pytest.fail("Stale or staged state leaked into a normal release")


def test_fact_failure_rolls_back_domain_and_index(catalog):
    table = "acquisition_facts"

    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith(f"INSERT INTO {table}"):
            raise RuntimeError("injected fact failure")

    event.listen(catalog.engine, "before_cursor_execute", fail)
    store = AcquisitionHandoffStore(catalog)
    try:
        with (
            pytest.raises(RuntimeError, match="injected"),
            catalog.writer_session() as session,
        ):
            session.execute(text("CREATE TABLE domain_probe (value TEXT)"))
            session.execute(text("INSERT INTO domain_probe VALUES ('advanced')"))
            store.stage_state_fact_in_session(session, fact())
    finally:
        event.remove(catalog.engine, "before_cursor_execute", fail)
    with catalog.Session() as session:
        if store.current_effective_state(session, fact().effective_key):
            pytest.fail("Failed fact advanced the effective index")
        tables = session.execute(
            text("SELECT name FROM sqlite_master WHERE name='domain_probe'")
        ).all()
        if tables:
            pytest.fail("Failed fact did not roll back caller domain transaction")


def test_equivalent_recovery_once_and_delayed_stale_release(catalog):
    first = stage(catalog, fact())
    retry = stage(catalog, fact(run="run-2"))
    release(catalog, group("run-2"), [entry(retry)])
    store = AcquisitionHandoffStore(catalog)
    entries = store.list_release_entries("source", Stream.OUTLOOK_MAIL)
    if len(entries) != 1:
        pytest.fail("Equivalent retry failed to recover unreleased state")
    members = store.load_release_facts(entries[0]["release_entry_seq"])
    if first.fact_id not in {member.fact_id for member in members}:
        pytest.fail("Recovery must bind the unreleased advanced fact")
    again = stage(catalog, fact(run="run-3"))
    release(catalog, group("run-3"), [entry(again)])
    if len(store.list_release_entries("source", Stream.OUTLOOK_MAIL)) != 1:
        pytest.fail("Already released equivalent state caused repeated work")
    stage(catalog, fact(state="v2", run="run-4"))
    release(catalog, group("run-1"), [entry(first)])
    if len(store.list_release_entries("source", Stream.OUTLOOK_MAIL)) != 1:
        pytest.fail("Delayed older completion published superseded state")


def test_preledger_equivalent_does_not_invent_advanced_state(catalog):
    old = stage(catalog, fact(storage_relation=Relation.CURRENT_EQUIVALENT))
    release(catalog, group(), [entry(old)])
    if AcquisitionHandoffStore(catalog).list_release_entries(
        "source", Stream.OUTLOOK_MAIL
    ):
        pytest.fail("Future-only baseline admitted unchanged historical state")


def test_group_idempotence_paging_and_digest_mismatch(catalog):
    facts = [stage(catalog, fact(resource=f"message-{i}")) for i in range(7)]
    spec = group()
    result = release(catalog, spec, list(map(entry, facts)))
    if release(catalog, spec, list(map(entry, facts))) != result:
        pytest.fail("Repeated publication changed identity")
    with pytest.raises(ValueError, match="digest|identity"):
        release(catalog, spec, [entry(facts[0])])
    store = AcquisitionHandoffStore(catalog)
    cursor = 0
    seen = []
    for _ in range(4):
        page = store.list_release_entries(
            "source", Stream.OUTLOOK_MAIL, after_seq=cursor, limit=2
        )
        seen.extend(row["release_entry_seq"] for row in page)
        if page:
            cursor = page[-1]["release_entry_seq"]
    if len(seen) != 7 or seen != sorted(set(seen)):
        pytest.fail("Large atomic group is not monotonically pageable")
    if store.list_release_entries("other", Stream.OUTLOOK_MAIL):
        pytest.fail("Feed crossed source boundary")


@pytest.mark.parametrize(
    "table",
    [
        "acquisition_facts",
        "acquisition_release_groups",
        "acquisition_release_entries",
        "acquisition_release_entry_facts",
    ],
)
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_immutable_ledger_rows(catalog, table, operation):
    f = stage(catalog, fact())
    release(catalog, group(), [entry(f)])
    column = {
        "acquisition_facts": "fact_id",
        "acquisition_release_groups": "release_group_id",
        "acquisition_release_entries": "release_entry_seq",
        "acquisition_release_entry_facts": "fact_id",
    }[table]
    sql = f"DELETE FROM {table}"
    if operation == "UPDATE":
        sql = f"UPDATE {table} SET {column}={column}"
    with (
        pytest.raises(DatabaseError, match="immutable"),
        catalog.writer_session() as session,
    ):
        session.execute(text(sql))


def test_core_connection_and_authority_promotion_rollback(catalog):
    store = AcquisitionHandoffStore(catalog)
    with catalog.engine.begin() as connection:
        staged = store.stage_authority_fact_in_session(connection, fact())
    with (
        pytest.raises(RuntimeError, match="rollback"),
        catalog.engine.begin() as connection,
    ):
        store.release_authority_group_in_session(
            connection,
            replace(group(), release_kind=ReleaseKind.AUTHORITY_SCOPE),
            [entry(staged)],
            winning_fact_ids=(staged.fact_id,),
        )
        raise RuntimeError("rollback")
    if store.list_release_entries("source", Stream.OUTLOOK_MAIL):
        pytest.fail("Rolled-back authority publication escaped transaction")
    with catalog.engine.begin() as connection:
        store.release_authority_group_in_session(
            connection,
            replace(group(), release_kind=ReleaseKind.AUTHORITY_SCOPE),
            [entry(staged)],
            winning_fact_ids=(staged.fact_id,),
        )
    if len(store.list_release_entries("source", Stream.OUTLOOK_MAIL)) != 1:
        pytest.fail("Winning authority did not publish staged state")


def test_empty_group_is_valid(catalog):
    release(catalog, group(), [])
    with catalog.Session() as session:
        count = session.execute(
            text("SELECT count(*) FROM acquisition_release_groups")
        ).scalar_one()
    if count != 1:
        pytest.fail("Empty authority/completion group was not retained")


def test_component_impact_retains_already_released_primary(catalog):
    primary = stage(catalog, fact())
    release(catalog, group(), [entry(primary)])
    component = stage(
        catalog,
        replace(
            fact(state="mime", run="run-2"),
            fact_kind=Kind.COMPONENT_OBSERVATION,
            resource_kind="mime",
            resource_identity="message-1",
            parent_resource_kind="message",
            parent_resource_identity="message-1",
            component_kind="mime",
        ),
    )
    release(
        catalog,
        group("run-2"),
        [
            replace(
                entry(primary),
                facts=(
                    (primary.fact_id, "primary"),
                    (component.fact_id, "component"),
                ),
            )
        ],
    )
    store = AcquisitionHandoffStore(catalog)
    newest = store.list_release_entries("source", Stream.OUTLOOK_MAIL)[-1]
    members = store.load_release_facts(newest["release_entry_seq"])
    if {f.fact_id for f in members} != {primary.fact_id, component.fact_id}:
        pytest.fail("Component impact lost exact unchanged primary association")


def test_publication_retry_does_not_depend_on_wall_clock(catalog):
    f = stage(catalog, fact())
    original = release(catalog, group(), [entry(f)])
    repeated = release(
        catalog,
        replace(
            group(),
            released_at="2026-10-04T00:00:00Z",
        ),
        [entry(f)],
    )
    if original != repeated:
        pytest.fail("Publication retry changed logical group identity")


def test_entry_cannot_claim_unrelated_resource(catalog):
    f = stage(catalog, fact())
    with pytest.raises(ValueError, match="resource|parent"):
        release(catalog, group(), [replace(entry(f), resource_identity="unrelated")])


def test_duplicate_impact_in_group_is_rejected(catalog):
    f = stage(catalog, fact())
    with pytest.raises(ValueError, match="duplicate|Duplicate"):
        release(catalog, group(), [entry(f), entry(f)])


def test_authority_staging_cannot_reuse_normal_fact_identity(catalog):
    f = stage(catalog, fact())
    store = AcquisitionHandoffStore(catalog)
    with catalog.writer_session() as session:
        staged = store.stage_authority_fact_in_session(session, fact())
    if (
        staged.fact_id == f.fact_id
        or staged.storage_relation != Relation.AUTHORITY_STAGED
    ):
        pytest.fail("Authority staging reused a normal observation")


def test_same_semantic_state_return_after_change_is_new_work(catalog):
    for run, state in (("one", "v1"), ("two", "v2"), ("three", "v1")):
        f = stage(catalog, fact(run=run, state=state))
        release(catalog, group(run), [entry(f)])
    entries = AcquisitionHandoffStore(catalog).list_release_entries(
        "source", Stream.OUTLOOK_MAIL
    )
    if len(entries) != 3:
        pytest.fail("Returning to an earlier semantic state lost the new advancement")


def test_unchanged_winning_authority_does_not_repeat_entries(catalog):
    store = AcquisitionHandoffStore(catalog)
    for run in ("one", "two"):
        with catalog.writer_session() as session:
            staged = store.stage_authority_fact_in_session(session, fact(run=run))
            store.release_authority_group_in_session(
                session,
                replace(group(run), release_kind=ReleaseKind.AUTHORITY_SCOPE),
                [entry(staged)],
                winning_fact_ids=(staged.fact_id,),
            )
    if len(store.list_release_entries("source", Stream.OUTLOOK_MAIL)) != 1:
        pytest.fail("Unchanged winning authority generated recurring work")


def test_incomplete_profile_entry_cannot_drop_stale_required_members(catalog):
    primary = stage(catalog, fact())
    component = stage(
        catalog,
        replace(
            fact(state="mime"),
            fact_kind=Kind.COMPONENT_OBSERVATION,
            resource_kind="mime",
            component_kind="mime",
            parent_resource_kind="message",
            parent_resource_identity="message-1",
        ),
    )
    stage(catalog, fact(state="v2", run="run-2"))
    release(
        catalog,
        replace(group(), release_kind=ReleaseKind.RESOURCE_PROFILE),
        [
            replace(
                entry(primary),
                facts=(
                    (primary.fact_id, "primary"),
                    (component.fact_id, "component"),
                ),
            ),
        ],
    )
    if AcquisitionHandoffStore(catalog).list_release_entries(
        "source", Stream.OUTLOOK_MAIL
    ):
        pytest.fail("Profile published after dropping a stale required primary")


def test_transition_cannot_be_relabelled_to_another_scope(catalog):
    transition = stage(
        catalog,
        replace(
            fact(),
            fact_kind=Kind.SCOPED_STATE_TRANSITION,
            scope_kind="folder",
            scope_identity="folder-a",
        ),
    )
    with pytest.raises(ValueError, match="scope"):
        release(
            catalog,
            group(),
            [
                replace(
                    entry(transition),
                    entry_kind="transition",
                    scope_kind="folder",
                    scope_identity="folder-b",
                )
            ],
        )


def test_authority_rejects_ambiguous_final_effective_state(catalog):
    store = AcquisitionHandoffStore(catalog)
    with catalog.writer_session() as session:
        first = store.stage_authority_fact_in_session(session, fact(state="v1"))
        second = store.stage_authority_fact_in_session(session, fact(state="v2"))
    with (
        pytest.raises(ValueError, match="winning|effective"),
        catalog.writer_session() as session,
    ):
        store.release_authority_group_in_session(
            session,
            replace(group(), release_kind=ReleaseKind.AUTHORITY_SCOPE),
            [entry(second)],
            winning_fact_ids=(first.fact_id, second.fact_id),
        )
