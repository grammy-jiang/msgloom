"""Calendar facts retain exact provenance inside provider writer transactions."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from calendar_handoff_helpers import (
    LATER,
    NOW,
    _capture,
    _fact,
    _facts,
    _item,
    _persist,
    _seed_content,
)
from calendar_handoff_helpers import (
    env as calendar_env,
)
from sqlalchemy.exc import IntegrityError
from test_calendar_pipeline import _event, _process, _raw

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    FactSpec,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
    StorageRelation,
)
from message_ingest.catalog.models.microsoft.outlook.calendar import (
    CalendarEventObservation,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.items.microsoft.outlook.calendar import (
    OutlookCalendarAttachmentContentItem,
    OutlookCalendarAttachmentItem,
    OutlookCalendarEventItem,
    OutlookCalendarEventSurfaceItem,
)

env = calendar_env


@pytest.mark.parametrize(
    "kind,component",
    [
        ("event", None),
        ("calendar", None),
        ("attachment", "attachment_metadata"),
        ("series", "series_topology"),
        ("surface", "detail"),
        ("content", "attachment_content"),
    ],
)
def test_provider_outcomes_map_to_atomic_facts(env, kind, component):
    crawler, catalog, _ = env
    if kind == "content":
        _seed_content(crawler)
    for run, at, value in (
        ("first", NOW, "v1"),
        ("same", LATER, "v1"),
        ("changed", "2026-09-29T00:00:00+00:00", "v2"),
        ("stale", NOW, "old"),
    ):
        _capture(crawler, run, at=at, body=value.encode())
        _persist(crawler, _item(kind, run, run, at, value))
    expected = {
        "first": StorageRelation.ADVANCED,
        "same": StorageRelation.CURRENT_EQUIVALENT,
        "changed": StorageRelation.ADVANCED,
        "stale": StorageRelation.STALE,
    }
    for run, relation in expected.items():
        fact = _fact(catalog, run, component)
        if fact.storage_relation != relation:
            pytest.fail(f"{kind}/{run}: {fact.storage_relation} != {relation}")
        if component and (
            fact.parent_resource_kind != "calendar_event"
            or fact.parent_resource_identity != "event-1"
        ):
            pytest.fail("Calendar components must name their event parent")
        locator = fact.source_version_locator
        if locator is None or locator.evidence_id != run:
            pytest.fail("Expected exact immutable evidence association")
    first = _fact(catalog, "first", component)
    same = _fact(catalog, "same", component)
    if first.source_state_key != same.source_state_key:
        pytest.fail("Capture/run identities changed semantic state")
    if same.revalidated_fact_id != first.fact_id:
        pytest.fail("Equivalent retry did not pin original advanced fact")


def test_event_cache_replay_keeps_logical_run_and_observation_locator(env):
    crawler, catalog, _ = env
    original = _capture(crawler, "original")
    _persist(crawler, _item("event", "first", original.evidence_id, NOW, "v1"))
    replay = _raw("cache", origin="http_cache", observed_at=LATER)
    replay.response_body = b"payload"
    item = _item("event", "retry", "cache", LATER, "v1")
    _process(crawler, replay, item)
    fact = _fact(catalog, "retry")
    first = _fact(catalog, "first")
    if fact.evidence_id != "original" or fact.run_id != "retry":
        pytest.fail("Canonical evidence ownership replaced logical run provenance")
    if fact.storage_relation != StorageRelation.CURRENT_EQUIVALENT:
        pytest.fail("Cache replay must revalidate current semantic state")
    locator = first.source_version_locator
    if locator is None or locator.kind != "observation":
        pytest.fail("Non-delta event version must retain observation locator")
    with catalog.Session() as session:
        row = session.get(CalendarEventObservation, locator.observation_id)
        if row is None or row.evidence_id != locator.evidence_id:
            pytest.fail("Event locator does not resolve its exact observation")


def test_old_event_replay_cannot_revalidate_newer_primary_state(env):
    crawler, catalog, _ = env
    for run, at in (("v1", NOW), ("v2", LATER)):
        _capture(crawler, run, at=at)
        _persist(crawler, _item("event", run, run, at, run))
    _persist(crawler, _item("event", "old-retry", "v1", NOW, "v1"))
    if _fact(catalog, "old-retry").storage_relation != StorageRelation.STALE:
        pytest.fail("Old immutable observation replay must not advance freshness")


def test_full_detail_does_not_change_primary_semantic_version(env):
    crawler, catalog, _ = env
    _capture(crawler, "basic")
    _persist(crawler, _item("event", "basic-run", "basic", NOW, "v1"))
    _capture(crawler, "detail", at=LATER, body=b"detailed representation")
    item = _item("event", "full-run", "detail", LATER, "v1")
    if not isinstance(item, OutlookCalendarEventItem):
        pytest.fail("Expected event fixture")
    item.observation_kind = "full"
    item.raw["body"] = {"content": "secret body", "contentType": "text"}
    _persist(crawler, item)
    _persist(crawler, _item("surface", "full-run", "detail", LATER, "v1"))
    primary = _fact(catalog, "full-run")
    component = _fact(catalog, "full-run", "detail")
    if primary.storage_relation != StorageRelation.CURRENT_EQUIVALENT:
        pytest.fail("Full projection created a false primary semantic version")
    if component.storage_relation != StorageRelation.ADVANCED:
        pytest.fail("Full detail needs its independent component state")
    if "secret body" in json.dumps([f.__dict__ for f in _facts(catalog)], default=str):
        pytest.fail("Provider body leaked into the ledger")


def _release(catalog, fact: FactSpec, run: str):
    handoff = AcquisitionHandoffStore(catalog)
    group = ReleaseGroupSpec(
        source_id="source-1",
        stream=AcquisitionStream.OUTLOOK_CALENDAR,
        release_kind=ReleaseKind.RESOURCE_PROFILE,
        subject_kind="calendar_event",
        subject_identity="event-1",
        owner_run_id=run,
        released_at=LATER,
        coverage_kind="complete",
        profile="full-v1",
    )
    entry = ReleaseEntrySpec(
        resource_kind="calendar_event",
        resource_identity="event-1",
        facts=((fact.fact_id, "component"),),
    )
    with catalog.writer_session() as session:
        handoff.release_effective_group_in_session(session, group, [entry])
    return handoff.list_release_entries(
        source_id="source-1",
        stream=AcquisitionStream.OUTLOOK_CALENDAR,
    )


def test_delayed_full_fact_cannot_publish_after_component_superseded(env):
    crawler, catalog, _ = env
    _capture(crawler, "old")
    _persist(crawler, _item("surface", "old", "old", NOW, "v1"))
    old = _fact(catalog, "old", "detail")
    _capture(crawler, "new", at=LATER, body=b"new detail")
    _persist(crawler, _item("surface", "new", "new", LATER, "v2"))
    if _release(catalog, old, "old"):
        pytest.fail("Delayed Full completion published superseded component")
    new = _fact(catalog, "new", "detail")
    if len(_release(catalog, new, "new")) != 1:
        pytest.fail("Current component did not publish exactly once")
    if _fact(catalog, "old", "detail") != old:
        pytest.fail("New surface rewrote old immutable fact/locator")


def test_equivalent_component_recovers_unreleased_advance_once(env):
    crawler, catalog, _ = env
    for run in ("failed", "retry", "again"):
        _capture(crawler, run)
        _persist(crawler, _item("surface", run, run, NOW, "v1"))
    if len(_release(catalog, _fact(catalog, "retry", "detail"), "retry")) != 1:
        pytest.fail("Equivalent retry lost an unreleased component")
    if len(_release(catalog, _fact(catalog, "again", "detail"), "again")) != 1:
        pytest.fail("Unchanged already released component churned downstream work")


def test_delta_facts_are_staged_invisible_and_attempt_scoped(env):
    crawler, catalog, _ = env
    _capture(crawler, "delta")
    first = _item("delta", "delta-run", "delta", NOW, "v1")
    _persist(crawler, first)
    _persist(crawler, replace(first, attempt=1))
    rows = _facts(catalog)
    if len(rows) != 2:
        pytest.fail("Delta replay lost current attempt staging provenance")
    handoff = AcquisitionHandoffStore(catalog)
    for fact in rows:
        if fact.storage_relation != StorageRelation.AUTHORITY_STAGED:
            pytest.fail("Delta observation became current before authority promotion")
        with catalog.Session() as session:
            if handoff.current_effective_state(session, fact.effective_key):
                pytest.fail("Delta staging changed effective source state")
    if handoff.list_release_entries(
        source_id="source-1", stream=AcquisitionStream.OUTLOOK_CALENDAR
    ):
        pytest.fail("Delta observation leaked as a downstream entry")


def _snapshot(catalog):
    tables = (
        "calendars",
        "calendar_events",
        "calendar_event_observations",
        "calendar_event_sightings",
        "calendar_event_attachments",
        "calendar_event_surfaces",
        "calendar_series_topologies",
        "calendar_delta_observations",
        "acquisition_facts",
        "acquisition_effective_states",
    )
    with catalog.engine.connect() as connection:
        available = set(
            connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).scalars()
        )
        if not set(tables) <= available:
            pytest.fail("Rollback snapshot must cover every provider table")
        return {
            name: connection.exec_driver_sql(f'SELECT * FROM "{name}"').all()
            for name in tables
        }


@pytest.mark.parametrize(
    "kind",
    [
        "calendar",
        "event",
        "attachment",
        "series",
        "surface",
        "content",
        "delta",
    ],
)
@pytest.mark.parametrize("existing", [False, True])
def test_fact_insert_failure_rolls_back_provider_state(env, kind, existing):
    crawler, catalog, _ = env
    if kind == "content":
        _seed_content(crawler)
    if existing:
        _capture(crawler, "first")
        _persist(crawler, _item(kind, "first", "first", NOW, "v1"))
    _capture(crawler, "failing", at=LATER, body=b"new bytes")
    before = _snapshot(catalog)
    with catalog.writer_session() as session:
        session.connection().exec_driver_sql(
            "CREATE TRIGGER reject_calendar_fact BEFORE INSERT ON acquisition_facts "
            "BEGIN SELECT RAISE(ABORT, 'injected calendar fact failure'); END"
        )
    with pytest.raises(IntegrityError, match="injected calendar fact failure"):
        _persist(crawler, _item(kind, "failing", "failing", LATER, "v2"))
    if _snapshot(catalog) != before:
        pytest.fail("Fact failure committed provider state without its provenance")


def test_surface_store_exposes_storage_relation(env):
    crawler, _, store = env
    _capture(crawler, "surface")
    result = store.set_event_surface(
        event_id="event-1",
        surface="detail",
        status="acquired",
        evidence_id="surface",
        observed_at=NOW,
        run_id="surface-run",
        profile_version="full-v1",
        resource_version="v1",
    )
    if result != StorageRelation.ADVANCED:
        pytest.fail(f"Surface write did not return storage relation: {result}")


@pytest.mark.parametrize(
    "kind,component",
    [
        ("attachment", "attachment_metadata"),
        ("content", "attachment_content"),
    ],
)
def test_unchanged_component_bytes_still_bind_new_event_version(env, kind, component):
    crawler, catalog, _ = env
    if kind == "content":
        _seed_content(crawler)
    for run, at in (("v1", NOW), ("v2", LATER)):
        _capture(crawler, run, at=at)
        item = _item(kind, run, run, at, "same")
        if not isinstance(
            item,
            (
                OutlookCalendarAttachmentItem,
                OutlookCalendarAttachmentContentItem,
            ),
        ):
            pytest.fail("Expected attachment fixture")
        item.resource_version = run
        _persist(crawler, item)
    first, second = _fact(catalog, "v1", component), _fact(catalog, "v2", component)
    if first.source_state_key == second.source_state_key:
        pytest.fail("Component identity lost its event version binding")
    if second.storage_relation != StorageRelation.ADVANCED:
        pytest.fail("Same metadata must advance when its bound event version changes")


def test_delta_event_companion_cannot_become_effective_before_promotion(env):
    crawler, catalog, _ = env
    _capture(crawler, "delta")
    item = _item("event", "delta", "delta", NOW, "v1")
    if not isinstance(item, OutlookCalendarEventItem):
        pytest.fail("Expected event fixture")
    item.observation_kind = "delta"
    _persist(crawler, item)
    fact = _fact(catalog, "delta")
    if fact.storage_relation != StorageRelation.AUTHORITY_STAGED:
        pytest.fail("Delta companion leaked through the ordinary event path")


def test_primary_fallback_ignores_transport_and_full_only_fields(env):
    crawler, catalog, _ = env
    for run, at in (("basic", NOW), ("full", LATER)):
        _capture(crawler, run, at=at)
        item = replace(_event(run, at), run_id=run)
        item.raw.pop("changeKey")
        if run == "full":
            item.observation_kind = "full"
            item.raw["body"] = {"content": "Full-only content"}
            item.raw["@odata.context"] = "https://example.test/context"
        _persist(crawler, item)
    if (
        _fact(catalog, "full").source_state_key
        != _fact(catalog, "basic").source_state_key
    ):
        pytest.fail("Fallback primary version mixed Full-only fields into identity")


@pytest.mark.parametrize("surface", ["detail", "attachments"])
def test_transport_only_json_changes_do_not_advance_surface(env, surface):
    crawler, catalog, _ = env
    for run in ("first", "retry"):
        body = json.dumps(
            {
                "value": [{"id": "a1", "name": "agenda.txt"}],
                "@odata.context": f"https://example.test/{run}",
                "@odata.nextLink": f"https://example.test/?token={run}",
                "@microsoft.graph.downloadUrl": f"https://download.test/{run}",
                "access_token": run,
            }
        ).encode()
        _capture(crawler, run, body=body)
        item = _item("surface", run, run, NOW, "v1")
        if not isinstance(item, OutlookCalendarEventSurfaceItem):
            pytest.fail("Expected surface fixture")
        item.surface = surface
        _persist(crawler, item)
    first, retry = _fact(catalog, "first", surface), _fact(catalog, "retry", surface)
    if first.source_state_key != retry.source_state_key:
        pytest.fail("Transport-only JSON changes created a new component state")


def test_raw_attachment_surface_hashes_exact_bytes_even_for_json_content(env):
    crawler, catalog, _ = env
    for run, body in (("first", b'{"id":1}'), ("changed", b'{ "id": 1 }')):
        _capture(crawler, run, body=body)
        item = _item("surface", run, run, NOW, "v1")
        if not isinstance(item, OutlookCalendarEventSurfaceItem):
            pytest.fail("Expected surface fixture")
        item.surface = "attachment_raw:a1"
        _persist(crawler, item)
    first = _fact(catalog, "first", "attachment_raw:a1")
    changed = _fact(catalog, "changed", "attachment_raw:a1")
    if first.source_state_key == changed.source_state_key:
        pytest.fail("Raw attachment bytes must not use JSON semantic normalization")
