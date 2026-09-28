"""Catalog-driven planner for Outlook Mail Full-v1 acquisition."""

from __future__ import annotations

from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

from .profile import attachment_required_surfaces, surface_is_complete


def pending_full_v1_message_ids(
    store: OutlookMailStore,
    *,
    limit: int | None = None,
) -> tuple[str, ...]:
    """Return deterministic current messages whose Full-v1 surfaces are incomplete."""
    if limit is not None and limit < 0:
        raise ValueError("limit must be >= 0")
    pending: list[str] = []
    for message_id in store.list_message_ids():
        surfaces = store.get_surfaces(message_id=message_id)
        complete = all(
            surface_is_complete(surfaces, surface)
            for surface in ("detail", "mime", "attachments")
        )
        attachments_state = surfaces.get("attachments")
        if (
            complete
            and attachments_state is not None
            and attachments_state["status"] == "acquired"
        ):
            for attachment in store.get_attachments(message_id=message_id):
                if any(
                    not surface_is_complete(surfaces, surface)
                    for surface in attachment_required_surfaces(
                        attachment["attachment_type"],
                        attachment["attachment_id"],
                    )
                ):
                    complete = False
                    break
        if complete:
            continue
        pending.append(message_id)
        if limit is not None and len(pending) >= limit:
            break
    return tuple(pending)


__all__ = ["pending_full_v1_message_ids"]
