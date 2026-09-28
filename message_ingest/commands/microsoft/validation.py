"""Cross-path validation for the unified Microsoft command."""

from __future__ import annotations

import argparse

from scrapy.exceptions import UsageError


def require_profile_path(opts: argparse.Namespace) -> None:
    """Reject hierarchy segments that do not belong to ``microsoft profile``."""
    if opts.resource_or_action is not None or opts.action is not None:
        raise UsageError("use 'microsoft profile' with no extra path")
    if opts.message_ids:
        raise UsageError("microsoft profile does not accept MESSAGE_ID values")


def reject_options(opts: argparse.Namespace, *, allowed: set[str]) -> None:
    """Reject options that do not belong to the selected command path."""
    values = {
        "json": opts.json,
        "yes": opts.yes,
        "folder": opts.folder,
        "page_size": opts.page_size,
        "max_pages": opts.max_pages,
        "reconcile": opts.reconcile,
        "operation": opts.operation,
        "acquisition_profile": opts.acquisition_profile,
        "start": opts.start,
        "end": opts.end,
        "calendar": opts.calendar,
    }
    used = [
        name
        for name, value in values.items()
        if name not in allowed and value not in (None, False, "")
    ]
    if used:
        rendered = ", ".join(f"--{name.replace('_', '-')}" for name in used)
        raise UsageError(f"option(s) not valid for this Microsoft command: {rendered}")


__all__ = ["reject_options", "require_profile_path"]
