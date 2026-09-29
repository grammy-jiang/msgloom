"""Dispatch Microsoft To Do discovery through Scrapy's normal lifecycle."""

import argparse
from typing import Any

from scrapy.exceptions import UsageError

from message_ingest.commands._common import run_graph


def dispatch_todo(command: Any, opts: argparse.Namespace) -> None:
    """Accept only discovery and page size; preserve shared Scrapy options."""
    if opts.resource_or_action != "discover":
        raise UsageError("use 'microsoft todo discover'")
    if opts.action is not None or opts.message_ids:
        raise UsageError("To Do discover does not accept RESOURCE_ID values")
    # Unlike boolean flags, optional resource arguments use None for absence.
    # Explicit zero limits, empty IDs, and --no-reconcile are still unrelated.
    used = [
        name
        for name in (
            "mailbox",
            "folder",
            "max_pages",
            "reconcile",
            "operation",
            "acquisition_profile",
            "max_enrich",
            "start",
            "end",
            "calendar",
        )
        if getattr(opts, name, None) is not None
    ]
    used.extend(name for name in ("json", "yes") if getattr(opts, name, False))
    if used:
        rendered = ", ".join(f"--{name.replace('_', '-')}" for name in used)
        raise UsageError(f"option(s) not valid for To Do discovery: {rendered}")
    run_graph(
        command, "microsoft_todo_discover", {"page_size": str(opts.page_size or 100)}
    )


__all__ = ["dispatch_todo"]
