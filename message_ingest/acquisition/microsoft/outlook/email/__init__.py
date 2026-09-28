"""Outlook Mail acquisition policies."""

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
    "attachment_required_surfaces",
    "attachment_type_name",
    "surface_is_complete",
]
