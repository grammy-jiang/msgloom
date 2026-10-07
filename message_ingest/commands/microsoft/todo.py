"""Dispatch Microsoft To Do discovery and authoritative snapshot sync."""

import argparse
from typing import Any

from scrapy.exceptions import UsageError

from message_ingest.commands._common import run_graph


def dispatch_todo(command: Any, opts: argparse.Namespace) -> None:
    """Validate To Do read actions and enter the normal Scrapy lifecycle."""
    action = opts.resource_or_action
    if action not in {"discover", "sync"}:
        raise UsageError("use 'microsoft todo {discover|sync}'")
    if opts.action is not None or opts.message_ids:
        raise UsageError(f"To Do {action} does not accept RESOURCE_ID values")
    if command.settings is not None and command.settings.get("JOBDIR"):
        raise UsageError(f"To Do {action} does not support JOBDIR")
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
        raise UsageError(f"option(s) not valid for To Do {action}: {rendered}")
    spider = "microsoft_todo_sync" if action == "sync" else "microsoft_todo_discover"
    run_graph(command, spider, {"page_size": str(opts.page_size or 100)})


__all__ = ["dispatch_todo"]
