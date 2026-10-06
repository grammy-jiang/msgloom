"""Exact Mail selections defer components until their primary is accepted."""

import json

import pytest
from test_outlook_mail_handoff_facts import capture, facts
from test_outlook_mail_handoff_facts import setup as setup  # noqa: PLC0414

from message_ingest.catalog.stores.microsoft.outlook._email_handoff import (
    primary_projection,
    semantic_digest,
)

T1 = "2026-10-03T01:00:00+00:00"
T2 = "2026-10-03T02:00:00+00:00"
T3 = "2026-10-03T03:00:00+00:00"
PROFILE = "outlook-mail-full-v1"


def primary(crawler, store, version, selection, when):
    """Select a primary through the real domain freshness decision."""
    body = {"id": "m1", "changeKey": version}
    evidence = "detail-" + selection
    capture(crawler, selection, evidence, json.dumps(body).encode(), when)
    return store.record_message(
        run_id=selection,
        message=body,
        kind="detail",
        evidence_id=evidence,
        observed_at=when,
        selection_id=selection,
    )


@pytest.mark.parametrize("family", ["mime", "attachment_metadata"])
def test_pending_capture_survives_old_component_and_primary_commit(setup, family):
    """A delayed old parent cannot erase the selected future component."""
    crawler, _, store = setup
    try:
        old = primary(crawler, store, "v1", "old", T1)
    except TypeError as exc:
        pytest.fail(f"Exact immutable primary selection is missing: {exc}")
    body = {"id": "m1", "changeKey": "v2"}
    pin = semantic_digest(primary_projection(body))
    capture(crawler, "new", "detail-new", json.dumps(body).encode(), T2)
    capture(crawler, "new", "bytes-new", b"same bytes", T2)
    capture(crawler, "old", "bytes-old", b"same bytes", T3)

    def component(selection, parent, evidence, when):
        common = {
            "run_id": selection,
            "message_id": "m1",
            "evidence_id": evidence,
            "observed_at": when,
            "resource_version": parent,
            "profile_version": PROFILE,
            "selection_id": selection,
            "parent_evidence_id": "detail-" + selection,
        }
        if family == "mime":
            return store.set_surface(surface="mime", status="acquired", **common)
        return store.upsert_attachment(
            attachment={"id": "a", "name": selection},
            **common,
        )

    pending = component("new", pin, "bytes-new", T2)
    if pending.fact is not None:
        pytest.fail("Unaccepted selected primary produced an effective fact")
    if any(
        f.source_version_locator is not None
        and f.source_version_locator.resource_version == pin
        for f in facts(store)
    ):
        pytest.fail("Pending component leaked into the shared effective ledger")
    component("old", old.fact.source_state_key, "bytes-old", T3)
    new = primary(crawler, store, "v2", "new", T2)
    with store.catalog.Session() as session:
        if family == "mime":
            current = store._facts().effective_fact(
                session,
                "message_surface",
                "m1",
                "mime",
                "m1",
            )
        else:
            current = store._facts().effective_fact(
                session,
                "attachment",
                "a",
                family,
                "m1",
            )
    if current is None or current.source_version_locator is None:
        pytest.fail("Accepted primary lost its retained component")
    if current.source_version_locator.resource_version != new.fact.source_state_key:
        pytest.fail("Final component still names the delayed old parent")
    if current.evidence_id != "bytes-new":
        pytest.fail("Cross-parent capture time displaced selected evidence")


def _mime(crawler, store, selection, version, when, evidence=None):
    """Use the selection's saved exact detail; bytes do not order parents."""
    evidence = evidence or "mime-" + selection
    capture(crawler, selection, evidence, b"same MIME", when)
    return store.set_surface(
        run_id=selection,
        message_id="m1",
        surface="mime",
        status="acquired",
        evidence_id=evidence,
        observed_at=when,
        profile_version=PROFILE,
        resource_version=semantic_digest(
            primary_projection({"id": "m1", "changeKey": version})
        ),
        selection_id=selection,
        parent_evidence_id="detail-" + selection,
    )


def test_aba_applications_keep_old_recovery_and_release_pins(setup):
    """Accepted A/B/A/B/A states cannot reuse an obsolete application pin."""

    crawler, _, store = setup
    applications = []
    for index, version in enumerate(("A", "B", "A", "B", "A"), 1):
        selection = f"selection-{index}"
        when = f"2026-10-03T0{index}:00:00+00:00"
        primary(crawler, store, version, selection, when)
        outcome = _mime(crawler, store, selection, version, when)
        applications.append(outcome.fact)
        publish(store, outcome.fact, selection)
    if len({f.fact_id for f in applications}) != 5:
        pytest.fail("Actual ABA applications reused immutable advanced IDs")
    if applications[0].source_state_key != applications[4].source_state_key:
        pytest.fail("Provenance leaked into component semantic identity")
    before = len(publish(store, applications[-1], "repeated-release"))
    old = _mime(crawler, store, "selection-1", "A", T1)
    if len(publish(store, old.fact, "obsolete-recovery")) != before:
        pytest.fail("Obsolete selection recovered a later same-hash application")
    if (
        store.full_binding_state(message_id="m1")["surfaces"]["mime"]["evidence_id"]
        != "mime-selection-5"
    ):
        pytest.fail("Old capture displaced the current ABA application")


def test_pending_survives_reopen_and_equivalent_retry_releases_once(setup):
    """A pending capture survives process boundaries without self-promotion."""
    from message_ingest.catalog import Catalog
    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

    crawler, _, store = setup
    body = {"id": "m1", "changeKey": "A"}
    capture(crawler, "retry", "detail-retry", json.dumps(body).encode(), T1)
    outcome = _mime(crawler, store, "retry", "A", T1)
    if outcome.fact is not None:
        pytest.fail("Missing primary was not retained pending")
    reopened = Catalog(store.catalog.database_url)
    try:
        other = OutlookMailStore(reopened, source_id="source")
        if other.get_surfaces(message_id="m1"):
            pytest.fail("Reopen exposed pending captures")
        primary(crawler, other, "A", "retry", T1)
        recovered = _mime(crawler, other, "retry", "A", T1)
        if recovered.fact is None:
            pytest.fail("Accepted retry did not reconcile pending capture")
        if len(publish(other, recovered.fact, "recovery")) != 1:
            pytest.fail("Failed-run application was not recovered once")
        repeated = _mime(crawler, other, "retry", "A", T1)
        if len(publish(other, repeated.fact, "replay")) != 1:
            pytest.fail("Repeated exact application caused release churn")
    finally:
        reopened.close()


@pytest.mark.parametrize(
    "point",
    [
        "mail_application_bindings",
        "acquisition_facts",
        "message_surfaces",
        "acquisition_effective_states",
        "component_fact",
        "component_binding",
    ],
)
def test_primary_reconciliation_failure_is_atomic(setup, point):
    """
    Every primary-application failure retains only earlier saved captures.
    """
    from sqlalchemy import text
    from sqlalchemy.exc import DatabaseError

    crawler, _, store = setup
    body = {"id": "m1", "changeKey": "new"}
    capture(crawler, "pending", "detail-pending", json.dumps(body).encode(), T2)
    _mime(crawler, store, "pending", "new", T2)
    table, condition = {
        "component_fact": (
            "acquisition_facts",
            "WHEN json_extract(NEW.payload, '$.resource_kind')='message_surface' ",
        ),
        "component_binding": (
            "mail_application_bindings",
            "WHEN NEW.capture_id IS NOT NULL ",
        ),
    }.get(point, (point, ""))
    with store.catalog.writer_session() as session:
        session.execute(
            text(
                f"CREATE TRIGGER fail_application BEFORE INSERT ON {table} "
                f"{condition}"
                "BEGIN SELECT RAISE(ABORT, 'application failure'); END"
            )
        )
    with pytest.raises(DatabaseError, match="application failure"):
        primary(crawler, store, "new", "pending", T2)
    if facts(store) or store.get_message_state(message_id="m1") is not None:
        pytest.fail("Failed primary transaction left domain or ledger state")
    with store.catalog.writer_session() as session:
        session.execute(text("DROP TRIGGER fail_application"))
    primary(crawler, store, "new", "pending", T2)
    if "mime" not in store.full_binding_state(message_id="m1")["surfaces"]:
        pytest.fail("Rollback lost the independently committed capture")


def test_capture_failure_does_not_change_primary_or_component(setup):
    """A failed capture insert cannot leave an applied projection/fact."""
    from sqlalchemy import text
    from sqlalchemy.exc import DatabaseError

    crawler, _, store = setup
    primary(crawler, store, "A", "current", T1)
    before = [f.fact_id for f in facts(store)]
    with store.catalog.writer_session() as session:
        session.execute(
            text(
                "CREATE TRIGGER fail_capture BEFORE INSERT ON mail_component_captures "
                "BEGIN SELECT RAISE(ABORT, 'capture failure'); END"
            )
        )
    with pytest.raises(DatabaseError, match="capture failure"):
        _mime(crawler, store, "current", "A", T2)
    if [f.fact_id for f in facts(store)] != before:
        pytest.fail("Failed capture changed immutable ledger history")
    if "mime" in store.get_surfaces(message_id="m1"):
        pytest.fail("Failed capture changed its projection")


def test_stale_primary_and_late_same_parent_capture_never_replace_winner(setup):
    """Primary and same-parent freshness decisions remain authoritative."""
    crawler, _, store = setup
    primary(crawler, store, "B", "winner", T2)
    winning = _mime(crawler, store, "winner", "B", T2)
    primary(crawler, store, "A", "loser", T1)
    pending = _mime(crawler, store, "loser", "A", T3)
    if pending.fact is not None:
        pytest.fail("Losing primary's late component fabricated advancement")
    _mime(crawler, store, "winner", "B", T1, evidence="old-canonical")
    state = store.full_binding_state(message_id="m1")
    if state["surfaces"]["mime"]["evidence_id"] != winning.fact.evidence_id:
        pytest.fail("Stale same-parent capture displaced accepted component")


def publish(store, fact, run):
    """Exercise existing release APIs with a component's owning message."""
    from message_ingest.acquisition.handoff import (
        AcquisitionStream,
        ReleaseEntrySpec,
        ReleaseGroupSpec,
        ReleaseKind,
    )
    from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore

    ledger = AcquisitionHandoffStore(store.catalog)
    group = ReleaseGroupSpec(
        source_id=store.source_id,
        stream=AcquisitionStream.OUTLOOK_MAIL,
        release_kind=ReleaseKind.RESOURCE_SET,
        subject_kind="mailbox",
        subject_identity="fixture",
        owner_run_id=run,
        released_at=T3,
        coverage_kind="complete",
    )
    entry = ReleaseEntrySpec(
        resource_kind="message",
        resource_identity="m1",
        facts=((fact.fact_id, "component"),),
    )
    with store.catalog.writer_session() as session:
        ledger.release_effective_group_in_session(session, group, [entry])
    return ledger.list_release_entries(store.source_id, AcquisitionStream.OUTLOOK_MAIL)


def test_delayed_exact_primary_replay_keeps_original_application(setup):
    """
    A stale repeat retains its original selection without claiming current.
    """
    crawler, _, store = setup
    old = primary(crawler, store, "A", "old", T1)
    primary(crawler, store, "B", "current", T2)
    repeated = primary(crawler, store, "A", "old", T1)
    if repeated.fact.source_state_key != old.fact.source_state_key:
        pytest.fail("Exact replay changed original primary semantics")
    pending = _mime(crawler, store, "old", "A", T3)
    if pending.fact is not None:
        pytest.fail("Obsolete primary replay promoted its component")
    if store.full_binding_state(message_id="m1")["selection_id"] != "current":
        pytest.fail("Stale primary replay displaced the current application")


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", {"unexpected": "object"}),
        ("name", "x" * 4097),
        ("size", -1),
        ("size", True),
        ("isInline", "false"),
        ("@odata.type", ["file"]),
        ("contentType", {"mime": "text/plain"}),
    ],
)
def test_attachment_projection_rejects_unknown_or_oversized_values(
    setup,
    field,
    value,
):
    """Untrusted metadata must fit the retained projection contract."""
    crawler, _, store = setup
    outcome = primary(crawler, store, "A", "selected", T1)
    capture(crawler, "selected", "metadata", b"metadata", T2)
    before = [fact.fact_id for fact in facts(store)]
    with pytest.raises(ValueError):
        store.upsert_attachment(
            run_id="selected",
            message_id="m1",
            attachment={"id": "a", field: value},
            evidence_id="metadata",
            observed_at=T2,
            resource_version=outcome.fact.source_state_key,
            selection_id="selected",
            parent_evidence_id="detail-selected",
        )
    if [fact.fact_id for fact in facts(store)] != before:
        pytest.fail("Invalid metadata mutated immutable ledger state")


def test_independent_catalog_writers_and_sources_keep_exact_selections(setup):
    """Writer reservations serialize duplicates without crossing source IDs."""
    from concurrent.futures import ThreadPoolExecutor

    from test_mail_inventory_bindings import page_evidence

    from message_ingest.catalog import Catalog
    from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

    crawler, _, store = setup
    primary(crawler, store, "A", "selected", T1)
    capture(crawler, "selected", "concurrent", b"same MIME", T2)
    other_catalog = Catalog(store.catalog.database_url)
    other = OutlookMailStore(other_catalog, source_id=store.source_id)

    def persist(target):
        return target.set_surface(
            run_id="selected",
            message_id="m1",
            surface="mime",
            status="acquired",
            profile_version=PROFILE,
            evidence_id="concurrent",
            observed_at=T2,
            selection_id="selected",
            parent_evidence_id="detail-selected",
            resource_version=semantic_digest(
                primary_projection({"id": "m1", "changeKey": "A"})
            ),
        ).fact.fact_id

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(persist, (store, other)))
        if len(set(outcomes)) != 1:
            pytest.fail("Serialized identical applications churned facts")
        independent = OutlookMailStore(other_catalog, source_id="independent")
        page_evidence(
            independent, "independent-detail", "m1", {"id": "m1", "changeKey": "B"}, T2
        )
        independent.record_message(
            run_id="selected",
            message={"id": "m1", "changeKey": "B"},
            kind="detail",
            evidence_id="independent-detail",
            observed_at=T2,
            selection_id="selected",
        )
        if independent.full_binding_state(message_id="m1")["surfaces"].get("mime"):
            pytest.fail("Equal target/selection names crossed source boundaries")
        if (
            store.full_binding_state(message_id="m1")["surfaces"]["mime"]["evidence_id"]
            != "concurrent"
        ):
            pytest.fail("Other source displaced an existing exact component")
    finally:
        other_catalog.close()
