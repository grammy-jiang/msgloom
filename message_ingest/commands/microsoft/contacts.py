"""Dispatch read-only personal Contacts snapshots through normal Scrapy lifecycle."""

import argparse
from typing import Any

from scrapy.exceptions import UsageError

from message_ingest.commands._common import run_graph


def dispatch_contacts(command: Any, opts: argparse.Namespace) -> None:
    """Expose additive discovery and authoritative snapshot sync only."""
    action = opts.resource_or_action
    if action not in {"discover", "sync"}:
        raise UsageError("use 'microsoft contacts {discover,sync}'")
    if opts.action is not None or opts.message_ids:
        raise UsageError(f"Contacts {action} does not accept RESOURCE_ID values")
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
        raise UsageError(f"option(s) not valid for Contacts {action}: {rendered}")
    run_graph(
        command,
        f"microsoft_contacts_{action}",
        {"page_size": str(opts.page_size or 100)},
    )


__all__ = ["dispatch_contacts"]
