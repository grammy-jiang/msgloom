"""Outlook Calendar acquisition policies and planning."""

from .planner import CalendarEnrichmentTarget, pending_full_v1_targets
from .profile import (
    FULL_V1,
    TERMINAL_SURFACE_STATUSES,
    attachment_required_surfaces,
    attachment_type_name,
    surface_is_complete,
)

__all__ = [
    "FULL_V1",
    "TERMINAL_SURFACE_STATUSES",
    "CalendarEnrichmentTarget",
    "attachment_required_surfaces",
    "attachment_type_name",
    "pending_full_v1_targets",
    "surface_is_complete",
]
