"""Reject false per-target completion at immutable evidence boundaries."""

from __future__ import annotations

import pytest
from _full_completion_fixtures import (
    LATER,
    NOW,
    save,
    seed_target,
    set_surface,
)
from test_calendar_full_completion import verify

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentItem,
    OutlookCalendarEventItem,
    OutlookCalendarSeriesTopologyItem,
)


@pytest.fixture
def catalog(tmp_path):
    value = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    yield value
    value.close()


def test_inventory_entry_without_metadata_cannot_be_complete(catalog):
    """Final-page success cannot conceal failed attachment persistence."""
    store = seed_target(catalog, "calendar")
    evidence = save(
        catalog,
        "with-child",
        {
            "value": [
                {"id": "a1", "@odata.type": "#microsoft.graph.fileAttachment"},
            ]
        },
    )
    set_surface(store, "calendar", "one", "attachments", evidence)
    if verify(catalog).complete:
        pytest.fail("Inventory child without an immutable metadata fact was ignored")


def test_item_attachment_requires_both_exact_child_surfaces(catalog):
    store = seed_target(catalog, "calendar")
    raw = {"id": "a1", "@odata.type": "#microsoft.graph.itemAttachment"}
    evidence = save(catalog, "with-child", {"value": [raw]})
    set_surface(store, "calendar", "one", "attachments", evidence)
    store.persist_attachment_metadata(
        OutlookCalendarAttachmentItem(
            event_id="one",
            attachment_id="a1",
            attachment_type=raw["@odata.type"],
            raw=raw,
            observed_at=NOW,
            evidence_id=evidence,
            run_id="run",
            resource_version="v1",
        )
    )
    if verify(catalog).complete:
        pytest.fail("Missing child bytes completed the parent")
    content = save(catalog, "child-content", {"saved": "raw"})
    set_surface(store, "calendar", "one", "attachment_raw:a1", content)
    if verify(catalog).complete:
        pytest.fail("Missing expanded item detail completed the parent")
    detail = save(catalog, "child-detail", raw)
    set_surface(store, "calendar", "one", "item_attachment_detail:a1", detail)
    result = verify(catalog)
    if not result.complete or len(result.required_facts) != 6:
        pytest.fail(f"Exact item attachment proof was incomplete: {result}")


@pytest.mark.parametrize("event_type", ["seriesMaster", "occurrence", "exception"])
def test_recurring_event_needs_terminal_series_topology(catalog, event_type):
    store = seed_target(catalog, "calendar")
    master = "one" if event_type == "seriesMaster" else "master"
    payload = {
        "id": "one",
        "changeKey": "v2",
        "type": event_type,
        "seriesMasterId": master,
    }
    evidence = save(catalog, "recurring", payload, at=LATER)
    store.persist_event(
        OutlookCalendarEventItem(
            event_id="one",
            raw=payload,
            observed_at=LATER,
            evidence_id=evidence,
            run_id="run",
            observation_kind="full",
        )
    )
    for surface, capture in (
        ("detail", evidence),
        ("attachments", "calendar-one-run-attachments"),
    ):
        set_surface(store, "calendar", "one", surface, capture, version="v2", at=LATER)
    if verify(catalog).complete:
        pytest.fail("Recurring event completed without topology")
    topology = save(catalog, "topology", {"id": master}, at=LATER)
    store.persist_series_topology(
        OutlookCalendarSeriesTopologyItem(
            series_master_id=master,
            calendar_id="default",
            status="unsupported",
            raw=None,
            observed_at=LATER,
            evidence_id=topology,
            run_id="run",
        )
    )
    result = verify(catalog)
    if not result.complete or result.limitation_codes != ("unsupported",):
        pytest.fail(f"Terminal topology did not satisfy profile: {result}")


def test_no_change_key_does_not_allow_stale_detail_revalidation(catalog):
    """A null provider version cannot stand in for equal primary state."""
    store = seed_target(catalog, "calendar", version=None)
    changed = {"id": "one", "subject": "newer event", "type": "singleInstance"}
    evidence = save(catalog, "changed-primary", changed, run="other", at=LATER)
    store.persist_event(
        OutlookCalendarEventItem(
            event_id="one",
            raw=changed,
            observed_at=LATER,
            evidence_id=evidence,
            run_id="other",
        )
    )
    if verify(catalog, run="reuse", current=False).complete:
        pytest.fail("Unversioned stale detail was attached to newer primary")


def test_fact_bound_returns_incomplete_instead_of_truncating(catalog):
    store = seed_target(catalog, "calendar")
    members = []
    for number in range(129):
        raw = {"id": f"a{number}", "@odata.type": "#microsoft.graph.fileAttachment"}
        members.append(raw)
        evidence = save(catalog, f"child-{number}", {"value": [raw]})
        store.persist_attachment_metadata(
            OutlookCalendarAttachmentItem(
                event_id="one",
                attachment_id=raw["id"],
                attachment_type=raw["@odata.type"],
                raw=raw,
                observed_at=NOW,
                evidence_id=evidence,
                run_id="run",
                resource_version="v1",
            )
        )
    inventory = save(catalog, "oversized-inventory", {"value": members})
    set_surface(store, "calendar", "one", "attachments", inventory)
    result = verify(catalog)
    if result.complete or result.required_facts or result.reason_code != "fact_limit":
        pytest.fail("Oversized completion silently dropped required facts")


@pytest.mark.parametrize("family", ["mail", "calendar"])
def test_paginated_inventory_cannot_hide_earlier_failed_metadata(catalog, family: str):
    """An empty final page cannot erase a failed earlier page's members."""
    from sqlalchemy import update

    from message_ingest.acquisition.microsoft.outlook.email.full_completion import (
        verify_full_v1_target as verify_mail,
    )
    from message_ingest.catalog.models.acquisition import RawHttpEvidence

    store = seed_target(catalog, family)
    root_url = "https://graph.test/me/resources/one/attachments"
    next_url = root_url + "?$skiptoken=page2"
    first = save(
        catalog,
        "page-one",
        {
            "value": [{"id": "lost", "@odata.type": "#microsoft.graph.fileAttachment"}],
            "@odata.nextLink": next_url,
        },
    )
    last = save(catalog, "page-two", {"value": []})
    with catalog.Session() as session, session.begin():
        for capture, url in ((first, root_url), (last, next_url)):
            session.execute(
                update(RawHttpEvidence)
                .where(
                    RawHttpEvidence.evidence_id == capture,
                )
                .values(request_url=url, response_url=url, purpose="attachments-list")
            )
    set_surface(
        store,
        family,
        "one",
        "attachments",
        last,
        version=None if family == "mail" else "v1",
    )
    result = (
        verify(catalog)
        if family == "calendar"
        else verify_mail(
            catalog,
            source_id="source",
            run_id="run",
            message_id="one",
        )
    )
    if result.complete:
        pytest.fail("Final page concealed failed earlier attachment persistence")

    raw = {"id": "lost", "@odata.type": "#microsoft.graph.fileAttachment"}
    if isinstance(store, OutlookMailStore):
        store.upsert_attachment(
            run_id="run",
            message_id="one",
            attachment=raw,
            evidence_id=first,
            observed_at=NOW,
        )
    else:
        store.persist_attachment_metadata(
            OutlookCalendarAttachmentItem(
                event_id="one",
                attachment_id="lost",
                attachment_type=raw["@odata.type"],
                raw=raw,
                observed_at=NOW,
                evidence_id=first,
                run_id="run",
                resource_version="v1",
            )
        )
    set_surface(
        store,
        family,
        "one",
        "attachment_raw:lost",
        first,
        status="unauthorized",
        version=None if family == "mail" else "v1",
    )
    result = (
        verify(catalog)
        if family == "calendar"
        else verify_mail(
            catalog,
            source_id="source",
            run_id="run",
            message_id="one",
        )
    )
    if not result.complete or not result.terminal_with_limitations:
        pytest.fail(f"Complete paginated inventory did not bind child proof: {result}")


def test_removed_historical_attachment_does_not_block_empty_inventory(catalog):
    """A current empty inventory excludes stale metadata from older runs."""
    store = seed_target(catalog, "calendar")
    raw = {"id": "old", "@odata.type": "#microsoft.graph.fileAttachment"}
    evidence = save(catalog, "old-attachment", {"value": [raw]}, run="old")
    store.persist_attachment_metadata(
        OutlookCalendarAttachmentItem(
            event_id="one",
            attachment_id="old",
            attachment_type=raw["@odata.type"],
            raw=raw,
            observed_at=NOW,
            evidence_id=evidence,
            run_id="old",
            resource_version="v1",
        )
    )
    result = verify(catalog)
    if not result.complete:
        pytest.fail(f"Historical attachment escaped current inventory scope: {result}")
