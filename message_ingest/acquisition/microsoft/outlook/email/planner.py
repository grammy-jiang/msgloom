"""Catalog-driven planner for Outlook Mail Full-v1 acquisition."""

from __future__ import annotations

from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore


def pending_full_v1_message_ids(
    store: OutlookMailStore,
    *,
    limit: int | None = None,
) -> tuple[str, ...]:
    """Return current messages with incomplete exact Full-v1 bindings."""
    if limit is not None and limit < 0:
        raise ValueError("limit must be >= 0")
    pending: list[str] = []
    for message_id in store.list_message_ids():
        if store.full_binding_complete(message_id=message_id):
            continue
        pending.append(message_id)
        if limit is not None and len(pending) >= limit:
            break
    return tuple(pending)


__all__ = ["pending_full_v1_message_ids"]
