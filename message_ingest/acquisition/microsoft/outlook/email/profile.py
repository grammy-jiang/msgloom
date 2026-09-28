"""
Define when Full-v1 enrichment may skip an already resolved surface.

A terminal result is complete only for the same profile version. This lets a
future profile retry surfaces that an older profile could not acquire.
"""

from __future__ import annotations

from typing import Any

from microsoft_graph.protocol.attachments import attachment_type_name

FULL_V1 = "outlook-mail-full-v1"

TERMINAL_SURFACE_STATUSES = frozenset(
    {
        "acquired",
        "unsupported",
        "not_applicable",
        "omitted_size_limit",
        "unauthorized",
        "unavailable",
    }
)


def surface_is_complete(surfaces: dict[str, dict[str, Any]], surface: str) -> bool:
    """Require both a terminal status and the current profile's version."""
    if (state := surfaces.get(surface)) is None:
        return False
    return (
        state["status"] in TERMINAL_SURFACE_STATUSES
        and state["profile_version"] == FULL_V1
    )


def attachment_required_surfaces(
    attachment_type: str | None, attachment_id: str
) -> tuple[str, ...]:
    """
    Require raw content for every type and expanded detail for item
    attachments.
    """
    if attachment_type_name(attachment_type) == "itemAttachment":
        return (
            f"attachment_raw:{attachment_id}",
            f"item_attachment_detail:{attachment_id}",
        )
    # Unknown provider attachment types must not silently count as complete.
    # Full-v1 records their raw/content surface as terminal unsupported until
    # a later profile learns how to acquire that provider type.
    return (f"attachment_raw:{attachment_id}",)
