"""Prove one Calendar Full-v1 target using exact effective facts."""

from __future__ import annotations

import json
from contextlib import nullcontext
from datetime import datetime

from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream, source_state_key
from message_ingest.acquisition.microsoft.outlook.email._full_facts import (
    FullFactReader,
    FullTargetCompletion,
    IncompleteProof,
    evidence_object,
    inventory_ids,
)
from message_ingest.catalog.models.microsoft.outlook.calendar import (
    CalendarEventAttachmentRecord,
    CalendarEventRecord,
    CalendarEventSurface,
    CalendarSeriesTopologyRecord,
)
from message_ingest.catalog.stores.handoff import Writer
from message_ingest.catalog.stores.microsoft.outlook._calendar_handoff import (
    event_projection,
)

from .profile import FULL_V1, attachment_required_surfaces, surface_is_complete


def verify_full_v1_target(
    catalog,
    *,
    source_id: str,
    run_id: str,
    event_id: str,
    require_current_attempt: bool = True,
    writer: Writer | None = None,
) -> FullTargetCompletion:
    """
    Revalidate one event without changing authority or acquisition state.

    Explicitly disable current-attempt requirements for planner-no-work or
    enrich reuse. This revalidates existing immutable facts without inventing
    acquisition provenance. With a caller writer, no transaction is opened.
    Publication must recheck freshness using the existing ledger API.
    """
    with nullcontext(writer) if writer is not None else catalog.Session() as session:
        reader = FullFactReader(
            catalog,
            session,
            source_id,
            AcquisitionStream.OUTLOOK_CALENDAR,
            run_id,
            require_current_attempt,
        )
        try:
            _verify(reader, event_id)
        except IncompleteProof as error:
            return FullTargetCompletion(
                "calendar_event",
                event_id,
                False,
                reason_code=str(error),
            )
        return reader.finish("calendar_event", event_id)


def _verify(reader: FullFactReader, event_id: str) -> None:
    """Require current primary, versioned surfaces, children and topology."""
    table = CalendarEventRecord.__table__
    event = (
        reader.writer.execute(
            select(table).where(
                table.c.source_id == reader.source_id,
                table.c.event_id == event_id,
            )
        )
        .mappings()
        .first()
    )
    if event is None or event["is_removed"]:
        raise IncompleteProof("missing_event")
    primary = reader.bind("calendar_event", event_id, effective_only=True)
    if primary.source_version_locator is None:
        raise IncompleteProof("missing_primary_locator")
    version = event["change_key"]
    if primary.source_version_locator.resource_version != version:
        raise IncompleteProof("primary_version_mismatch")
    # Component locators retain only changeKey, not the fallback primary key.
    # Neither a shared run nor observation time proves parent-state identity.
    # Keep fallback observations, but do not publish an unbound Full profile.
    if not version:
        raise IncompleteProof("unbound_parent_version")
    detail = _surface(reader, event_id, "detail", version)
    if detail[0] == "acquired":
        payload = evidence_object(reader, detail[1])
        if (
            payload.get("id") != event_id
            or source_state_key(event_projection(payload)) != primary.source_state_key
        ):
            raise IncompleteProof("primary_state_mismatch")
    inventory = _surface(reader, event_id, "attachments", version)
    if inventory[0] == "acquired":
        _attachments(reader, event_id, version, inventory[1])
    event_type = event["event_type"]
    master = event_id if event_type == "seriesMaster" else event["series_master_id"]
    if event_type in {"occurrence", "exception", "seriesMaster"}:
        if not master:
            raise IncompleteProof("missing_series_parent")
        _topology(reader, master, event["latest_observed_at"])


def _surface(reader, event_id, name, version):
    """Bind terminal profile metadata to its immutable evidence/version."""
    table = CalendarEventSurface.__table__
    row = (
        reader.writer.execute(
            select(table).where(
                table.c.source_id == reader.source_id,
                table.c.event_id == event_id,
                table.c.surface == name,
            )
        )
        .mappings()
        .first()
    )
    if row is None or not surface_is_complete(
        {name: row},
        name,
        resource_version=version,
    ):
        raise IncompleteProof("incomplete_surface")
    fact = reader.bind(
        "calendar_event_surface",
        event_id,
        component=name,
        parent=event_id,
        evidence_id=row["evidence_id"],
    )
    locator = fact.source_version_locator
    if (
        locator is None
        or locator.resource_version != version
        or json.loads(fact.transition_reason or "{}")
        != {
            "status": row["status"],
            "profile_version": FULL_V1,
        }
    ):
        raise IncompleteProof("surface_fact_mismatch")
    if row["status"] != "acquired":
        reader.limitations.add(row["status"])
    return row["status"], fact


def _attachments(reader, event_id, version, inventory):
    """Require exact metadata and child surfaces from this inventory."""
    table = CalendarEventAttachmentRecord.__table__
    required_ids = inventory_ids(reader, inventory)
    rows = (
        reader.writer.execute(
            select(table)
            .where(
                table.c.source_id == reader.source_id,
                table.c.event_id == event_id,
                table.c.attachment_id.in_(required_ids),
            )
            .order_by(table.c.attachment_id)
            .limit(129)
        )
        .mappings()
        .all()
    )
    if len(rows) > 128:
        raise IncompleteProof("fact_limit")
    present_ids = {row["attachment_id"] for row in rows}
    if not required_ids <= present_ids:
        raise IncompleteProof("missing_attachment_metadata")
    for row in rows:
        fact = reader.bind(
            "calendar_attachment",
            row["attachment_id"],
            component="attachment_metadata",
            parent=event_id,
            evidence_id=row["latest_evidence_id"],
            run_id=inventory.run_id,
        )
        locator = fact.source_version_locator
        if locator is None or locator.resource_version != version:
            raise IncompleteProof("attachment_version_mismatch")
        for name in attachment_required_surfaces(
            row["attachment_type"],
            row["attachment_id"],
        ):
            _surface(reader, event_id, name, version)


def _topology(reader, master, observed_at):
    """Apply existing terminal topology coverage to exact immutable proof."""
    table = CalendarSeriesTopologyRecord.__table__
    row = (
        reader.writer.execute(
            select(table).where(
                table.c.source_id == reader.source_id,
                table.c.series_master_id == master,
            )
        )
        .mappings()
        .first()
    )
    if row is None or row["status"] not in {
        "acquired",
        "unsupported",
        "unauthorized",
        "unavailable",
    }:
        raise IncompleteProof("incomplete_topology")
    if datetime.fromisoformat(row["latest_observed_at"]) < datetime.fromisoformat(
        observed_at,
    ):
        raise IncompleteProof("stale_topology")
    fact = reader.bind(
        "calendar_series",
        master,
        component="series_topology",
        parent=master,
        evidence_id=row["latest_evidence_id"],
    )
    if fact.transition_reason != row["status"]:
        raise IncompleteProof("topology_fact_mismatch")
    if row["status"] != "acquired":
        reader.limitations.add(row["status"])


__all__ = ["FullTargetCompletion", "verify_full_v1_target"]
