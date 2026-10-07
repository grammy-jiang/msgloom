"""Catalog-driven planner for Outlook Calendar full acquisition."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from message_ingest.catalog.stores.microsoft.outlook.calendar import (
    OutlookCalendarStore,
)

from .profile import attachment_required_surfaces, surface_is_complete


@dataclass(frozen=True, slots=True)
class CalendarEnrichmentTarget:
    """One event and containing calendar that still needs Full-v1 work."""

    event_id: str
    calendar_id: str
    resource_version: str | None


def pending_full_v1_targets(
    store: OutlookCalendarStore,
    *,
    run_ids: Iterable[str] | None = None,
    event_ids: Iterable[str] | None = None,
    limit: int | None = None,
) -> tuple[CalendarEnrichmentTarget, ...]:
    """Return deterministic incomplete events, optionally scoped to crawl runs."""
    if limit is not None and limit < 0:
        raise ValueError("limit must be >= 0")
    targets: list[CalendarEnrichmentTarget] = []
    for event_id, calendar_id, resource_version in store.list_event_targets(
        run_ids=run_ids,
        event_ids=event_ids,
    ):
        surfaces = store.get_event_surfaces(event_id=event_id)
        complete = surface_is_complete(
            surfaces, "detail", resource_version=resource_version
        ) and surface_is_complete(
            surfaces, "attachments", resource_version=resource_version
        )
        attachments_state = surfaces.get("attachments")
        if (
            complete
            and attachments_state is not None
            and attachments_state["status"] == "acquired"
        ):
            for attachment in store.get_event_attachments(event_id=event_id):
                if any(
                    not surface_is_complete(
                        surfaces, surface, resource_version=resource_version
                    )
                    for surface in attachment_required_surfaces(
                        attachment["attachment_type"],
                        attachment["attachment_id"],
                    )
                ):
                    complete = False
                    break
        if complete:
            event_state = store.get_event_state(event_id=event_id)
            if event_state is not None:
                event_type = event_state["event_type"]
                series_master_id = event_state["series_master_id"]
                if event_type == "seriesMaster":
                    series_master_id = event_id
                if (
                    event_type in {"occurrence", "exception", "seriesMaster"}
                    and series_master_id
                    and not store.series_topology_covers(
                        series_master_id=series_master_id,
                        observed_at=event_state["latest_observed_at"],
                    )
                ):
                    complete = False
        if complete:
            continue
        targets.append(
            CalendarEnrichmentTarget(event_id, calendar_id, resource_version)
        )
        if limit is not None and len(targets) >= limit:
            break
    return tuple(targets)


__all__ = ["CalendarEnrichmentTarget", "pending_full_v1_targets"]
