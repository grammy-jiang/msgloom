"""Reject Calendar component proofs without an exact parent version."""

from __future__ import annotations

import pytest
from _full_completion_fixtures import LATER, save, seed_target, set_surface

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.acquisition.microsoft.outlook.calendar.full_completion import (
    verify_full_v1_target,
)
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.items.microsoft.outlook.calendar import OutlookCalendarEventItem


@pytest.mark.parametrize("current", [True, False])
@pytest.mark.parametrize("changed", [True, False])
def test_unversioned_inventory_cannot_prove_parent_state(tmp_path, current, changed):
    """Same-run or same-time facts cannot replace an exact parent binding."""
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.db'}")
    try:
        store = seed_target(catalog, "calendar", version=None)
        if changed:
            raw = {
                "id": "one",
                "subject": "new event state",
                "type": "singleInstance",
                "hasAttachments": True,
                "changeKey": None,
            }
            evidence = save(catalog, "new-detail", raw, at=LATER)
            store.persist_event(
                OutlookCalendarEventItem(
                    event_id="one",
                    raw=raw,
                    observed_at=LATER,
                    evidence_id=evidence,
                    run_id="run",
                    observation_kind="full",
                )
            )
            set_surface(
                store,
                "calendar",
                "one",
                "detail",
                evidence,
                version=None,
                at=LATER,
            )
        proof = verify_full_v1_target(
            catalog,
            source_id="source",
            run_id="run" if current else "reuse",
            event_id="one",
            require_current_attempt=current,
        )
        entries = _publish_if_complete(catalog, proof)
        if entries:
            pytest.fail("Unbound fallback state published a release")
        if proof.complete or proof.required_facts:
            pytest.fail("Unbound fallback inventory produced a complete proof")
        if proof.reason_code != "unbound_parent_version":
            pytest.fail(f"Unexpected incomplete reason: {proof.reason_code}")
    finally:
        catalog.close()


@pytest.mark.parametrize("current", [True, False])
def test_versioned_inventory_still_proves_exact_target(tmp_path, current):
    """The fail-closed boundary retains useful versioned completion."""
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.db'}")
    try:
        seed_target(catalog, "calendar", version="v1")
        proof = verify_full_v1_target(
            catalog,
            source_id="source",
            run_id="run" if current else "reuse",
            event_id="one",
            require_current_attempt=current,
        )
        if not proof.complete or len(proof.required_facts) != 3:
            pytest.fail("Versioned target lost exact complete proof")
        if len(_publish_if_complete(catalog, proof)) != 1:
            pytest.fail("Versioned target did not publish its exact facts")
    finally:
        catalog.close()


def _publish_if_complete(catalog, proof):
    """Exercise the real ledger only when the public verifier admits release."""
    ledger = AcquisitionHandoffStore(catalog)
    if proof.complete:
        group = ReleaseGroupSpec(
            source_id="source",
            stream=AcquisitionStream.OUTLOOK_CALENDAR,
            release_kind=ReleaseKind.RESOURCE_PROFILE,
            subject_kind="calendar_event",
            subject_identity="one",
            owner_run_id="run",
            released_at=LATER,
            coverage_kind="complete",
            profile="outlook-calendar-full-v1",
        )
        entry = ReleaseEntrySpec(
            resource_kind="calendar_event",
            resource_identity="one",
            facts=tuple(
                (
                    fact.fact_id,
                    "primary" if fact.component_kind is None else "component",
                )
                for fact in proof.required_facts
            ),
        )
        with catalog.writer_session() as session:
            ledger.release_effective_group_in_session(session, group, [entry])
    return ledger.list_release_entries("source", AcquisitionStream.OUTLOOK_CALENDAR)
