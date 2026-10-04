"""Keep accepted repeated captures fresh without reviving old release rights."""

from dataclasses import replace

import pytest
from sqlalchemy import event, text
from test_acquisition_handoff_catalog import (
    Relation,
    Stream,
    entry,
    fact,
    group,
    release,
    stage,
)
from test_acquisition_handoff_catalog import catalog as _catalog

from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

catalog = _catalog


def current_fact(catalog, spec):
    """Read the effective pointer from the real catalog transaction boundary."""
    with catalog.Session() as writer:
        current = AcquisitionHandoffStore(catalog).current_effective_state(
            writer, spec.effective_key
        )
    if current is None:
        pytest.fail("Accepted state has no effective pointer")
    return current["fact_id"]


def test_exact_capture_reapplication_tracks_provider_order(catalog):
    """An early exact-staging return must not leave intervening B effective."""
    original = stage(catalog, fact())
    intervening = stage(catalog, fact(state="v2"))
    reapplied = stage(catalog, fact())
    if current_fact(catalog, original) != reapplied.fact_id:
        pytest.fail("Accepted A reapplication left B effective")
    if reapplied.fact_id in {original.fact_id, intervening.fact_id}:
        pytest.fail("Reapplication resurrected an old advancement identity")
    if reapplied.storage_relation != Relation.ADVANCED:
        pytest.fail("A genuinely reapplied state must be advanced")
    if (
        reapplied.source_state_key != original.source_state_key
        or reapplied.source_version_locator != original.source_version_locator
    ):
        pytest.fail("Reapplication invented a different semantic source version")
    release(catalog, group("delayed-B"), [entry(intervening)])
    release(catalog, group("delayed-A"), [entry(original)])
    if AcquisitionHandoffStore(catalog).list_release_entries(
        "source", Stream.OUTLOOK_MAIL
    ):
        pytest.fail("Reapplication revived superseded release rights")


@pytest.mark.parametrize("relation", [Relation.ADVANCED, Relation.CURRENT_EQUIVALENT])
def test_same_state_duplicate_reuses_latest_application(catalog, relation):
    """A retry must not create another occurrence or fall back to original A."""
    stage(catalog, fact())
    stage(catalog, fact(state="v2"))
    latest = stage(catalog, fact())
    duplicate = stage(catalog, fact(storage_relation=relation))
    if duplicate != latest or current_fact(catalog, latest) != latest.fact_id:
        pytest.fail("Exact retry did not reuse the effective application")
    with catalog.Session() as writer:
        count = writer.execute(text("SELECT count(*) FROM acquisition_facts")).scalar()
    if count != 3:
        pytest.fail("A/B/A followed by a duplicate must retain three facts")


def test_old_equivalent_pin_cannot_recover_a_reapplication(catalog):
    """An old A-equivalence proof must not gain rights when exact A returns."""
    original = stage(catalog, fact())
    old_retry = stage(catalog, fact(run="old-retry"))
    stage(catalog, fact(state="v2"))
    latest = stage(catalog, fact())
    if old_retry.revalidated_fact_id != original.fact_id:
        pytest.fail("Fixture did not pin the original advancement")
    if stage(catalog, fact(run="old-retry")) != old_retry:
        pytest.fail("Repeated old observation rewrote its recovery pin")
    release(catalog, group("old-retry"), [entry(old_retry)])
    if AcquisitionHandoffStore(catalog).list_release_entries(
        "source", Stream.OUTLOOK_MAIL
    ):
        pytest.fail("Old recovery proof became valid again after A/B/A")
    fresh_retry = stage(catalog, fact(run="fresh-retry"))
    release(catalog, group("fresh-retry"), [entry(fresh_retry)])
    store = AcquisitionHandoffStore(catalog)
    rows = store.list_release_entries("source", Stream.OUTLOOK_MAIL)
    if len(rows) != 1:
        pytest.fail("Fresh recovery did not publish the reapplied state once")
    if store.load_release_facts(rows[0]["release_entry_seq"]) != [latest]:
        pytest.fail("Recovery published the original A rather than reapplied A")


def test_stale_exact_replay_never_advances_pointer(catalog):
    """Both new and repeated stale staging must preserve the accepted winner."""
    original = stage(catalog, fact())
    winner = stage(catalog, fact(state="v2"))
    stale = replace(fact(), storage_relation=Relation.STALE)
    staged = stage(catalog, stale)
    for _ in range(2):
        repeated = stage(catalog, stale)
        if repeated != staged:
            pytest.fail("Stale exact staging is not idempotent")
        if staged.storage_relation != Relation.STALE:
            pytest.fail("Stale replay reused an advanced occurrence")
        if current_fact(catalog, original) != winner.fact_id:
            pytest.fail("Stale replay replaced the accepted effective state")
    release(catalog, group("stale"), [entry(staged)])
    if AcquisitionHandoffStore(catalog).list_release_entries(
        "source", Stream.OUTLOOK_MAIL
    ):
        pytest.fail("Stale replay published primary state")


def test_each_reapplication_releases_exactly_once(catalog):
    """Multiple A/B cycles must retain each advance without duplicate retries."""
    accepted = []
    for index, state in enumerate(("v1", "v2", "v1", "v2", "v1")):
        observed = fact(state=state)
        latest = stage(catalog, observed)
        accepted.append(latest.fact_id)
        release(catalog, group(f"release-{index}"), [entry(latest)])
        release(catalog, group(f"release-{index}"), [entry(latest)])
        duplicate = stage(
            catalog, replace(observed, storage_relation=Relation.CURRENT_EQUIVALENT)
        )
        release(catalog, group(f"duplicate-{index}"), [entry(duplicate)])
        retry = stage(catalog, fact(state=state, run=f"retry-{index}"))
        release(catalog, group(f"retry-{index}"), [entry(retry)])
    store = AcquisitionHandoffStore(catalog)
    rows = store.list_release_entries("source", Stream.OUTLOOK_MAIL)
    if len(rows) != 5 or len(set(accepted)) != 5:
        pytest.fail("Accepted reapplications were lost or duplicated")
    released = [
        store.load_release_facts(row["release_entry_seq"])[0].fact_id for row in rows
    ]
    if released != accepted:
        pytest.fail("Released facts do not match exact accepted applications")


def test_reapplication_fact_failure_rolls_back_domain_and_pointer(catalog):
    """A repeated capture needs a new atomic fact, not a silent early return."""
    stage(catalog, fact())
    winner = stage(catalog, fact(state="v2"))
    with catalog.writer_session() as writer:
        writer.execute(text("CREATE TABLE domain_reapplication (value TEXT)"))
        writer.execute(text("INSERT INTO domain_reapplication VALUES ('B')"))

    def reject(_conn, _cursor, statement, _parameters, _context, _many):
        if statement.startswith("INSERT INTO acquisition_facts"):
            raise RuntimeError("injected reapplication fact failure")

    event.listen(catalog.engine, "before_cursor_execute", reject)
    try:
        with (
            pytest.raises(RuntimeError, match="reapplication fact failure"),
            catalog.writer_session() as writer,
        ):
            writer.execute(text("UPDATE domain_reapplication SET value='A'"))
            AcquisitionHandoffStore(catalog).stage_state_fact_in_session(writer, fact())
    finally:
        event.remove(catalog.engine, "before_cursor_execute", reject)
    with catalog.Session() as writer:
        value = writer.execute(text("SELECT value FROM domain_reapplication")).scalar()
    if value != "B" or current_fact(catalog, winner) != winner.fact_id:
        pytest.fail("Failed reapplication committed domain or effective state")


def test_connection_reapplication_preserves_caller_rollback(catalog):
    """Calendar's Core Connection path obeys the same application boundary."""
    original = stage(catalog, fact())
    winner = stage(catalog, fact(state="v2"))
    store = AcquisitionHandoffStore(catalog)
    with (
        pytest.raises(RuntimeError, match="caller rollback"),
        catalog.writer_session() as session,
    ):
        writer = session.connection()
        latest = store.stage_state_fact_in_session(writer, fact())
        current = store.current_effective_state(writer, original.effective_key)
        if current is None or current["fact_id"] != latest.fact_id:
            pytest.fail("Core Connection did not track reapplication")
        raise RuntimeError("caller rollback")
    if current_fact(catalog, winner) != winner.fact_id:
        pytest.fail("Ledger committed the caller's rolled-back reapplication")
