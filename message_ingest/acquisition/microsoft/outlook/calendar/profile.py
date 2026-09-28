"""Versioned completeness policy for Outlook Calendar full acquisition."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from microsoft_graph.protocol.attachments import attachment_type_name

FULL_V1 = "outlook-calendar-full-v1"

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


def surface_is_complete(
    surfaces: Mapping[str, Mapping[str, Any]],
    surface: str,
    *,
    resource_version: str | None = None,
) -> bool:
    """Require terminal Full-v1 state for the current provider resource version."""
    if (state := surfaces.get(surface)) is None:
        return False
    return (
        state["status"] in TERMINAL_SURFACE_STATUSES
        and state["profile_version"] == FULL_V1
        and (
            resource_version is None
            or state.get("resource_version") == resource_version
        )
    )


def attachment_required_surfaces(
    attachment_type: str | None,
    attachment_id: str,
) -> tuple[str, ...]:
    """Require raw content for file/item attachments and expanded item detail."""
    if attachment_type_name(attachment_type) == "itemAttachment":
        return (
            f"attachment_raw:{attachment_id}",
            f"item_attachment_detail:{attachment_id}",
        )
    return (f"attachment_raw:{attachment_id}",)


__all__ = [
    "FULL_V1",
    "TERMINAL_SURFACE_STATUSES",
    "attachment_required_surfaces",
    "attachment_type_name",
    "surface_is_complete",
]
