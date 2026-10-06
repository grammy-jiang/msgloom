"""Verify catalog-driven Outlook Mail Full-v1 planning."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from outlook_mail_handoff_fixtures import saved_mail_evidence
from test_mail_inventory_bindings import seed_inventory

from message_ingest.acquisition.microsoft.outlook.email.planner import (
    pending_full_v1_message_ids,
)
from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

NOW = "2026-09-28T00:00:00+00:00"


def _store(tmp_path: Path) -> tuple[Catalog, OutlookMailStore]:
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    return catalog, OutlookMailStore(catalog, source_id="source-1")


def _message(
    store: OutlookMailStore, message_id: str, *, observed_at: str = NOW
) -> None:
    payload = {"id": message_id, "hasAttachments": False}
    evidence_id = saved_mail_evidence(
        store.catalog,
        evidence_id=f"primary-{message_id}",
        body=json.dumps(payload).encode(),
        observed_at=observed_at,
    )
    store.record_message(
        run_id="fixture-run",
        message=payload,
        kind="delta",
        selection_id=f"selection-{message_id}",
        evidence_id=evidence_id,
        observed_at=observed_at,
    )


def _pin(store, message_id):
    """Read the fixture's explicitly selected primary fact."""
    with store.catalog.Session() as session:
        fact = store._facts().effective_fact(session, "message", message_id)
        if fact is None:
            pytest.fail("Missing primary fixture")
        return fact.source_state_key


def _surface(
    store: OutlookMailStore,
    message_id: str,
    surface: str,
    *,
    status: str = "acquired",
    profile: str | None = FULL_V1,
) -> None:
    if surface == "attachments":
        seed_inventory(
            store,
            message_id,
            f"selection-{message_id}",
            _pin(store, message_id),
            f"primary-{message_id}",
            [],
            status=status,
            profile=profile,
        )
        return
    evidence_id = saved_mail_evidence(
        store.catalog,
        evidence_id=f"fixture-{message_id}-{surface}",
    )
    store.set_surface(
        run_id="fixture-run",
        message_id=message_id,
        resource_version=_pin(store, message_id),
        selection_id=f"selection-{message_id}",
        parent_evidence_id=f"primary-{message_id}",
        surface=surface,
        status=status,
        evidence_id=evidence_id,
        observed_at=NOW,
        profile_version=profile,
    )


def test_planner_selects_missing_base_surfaces_and_skips_complete_message(
    tmp_path: Path,
) -> None:
    catalog, store = _store(tmp_path)
    try:
        _message(store, "pending")
        _message(store, "complete")
        for surface in ("detail", "mime", "attachments"):
            _surface(store, "complete", surface)

        if pending_full_v1_message_ids(store) != ("pending",):
            pytest.fail("Expected only the incomplete Mail message")
    finally:
        catalog.close()


def test_planner_requires_attachment_surfaces_for_current_inventory(
    tmp_path: Path,
) -> None:
    catalog, store = _store(tmp_path)
    try:
        _message(store, "m1")
        for surface in ("detail", "mime", "attachments"):
            _surface(store, "m1", surface)
        seed_inventory(
            store,
            "m1",
            "selection-m1",
            _pin(store, "m1"),
            "primary-m1",
            [{"id": "a1", "@odata.type": "#microsoft.graph.itemAttachment"}],
        )
        _surface(store, "m1", "attachment_raw:a1")
        if pending_full_v1_message_ids(store) != ("m1",):
            pytest.fail("Expected missing item-attachment detail to keep Mail pending")
        _surface(store, "m1", "item_attachment_detail:a1")
        if pending_full_v1_message_ids(store):
            pytest.fail(
                "Expected complete item-attachment surfaces to clear Mail target"
            )
    finally:
        catalog.close()


def test_planner_requires_current_profile_version_and_honors_limit(
    tmp_path: Path,
) -> None:
    catalog, store = _store(tmp_path)
    try:
        for message_id in ("old-profile", "missing"):
            _message(store, message_id)
        for surface in ("detail", "mime", "attachments"):
            _surface(store, "old-profile", surface, profile="older-profile")

        pending = pending_full_v1_message_ids(store, limit=1)
        if len(pending) != 1 or pending[0] not in {"old-profile", "missing"}:
            pytest.fail(f"Unexpected bounded Mail planner result: {pending!r}")
        with pytest.raises(ValueError, match="limit"):
            pending_full_v1_message_ids(store, limit=-1)
    finally:
        catalog.close()
