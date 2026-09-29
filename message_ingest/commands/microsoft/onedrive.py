"""Dispatch read-only OneDrive acquisition through Scrapy's lifecycle."""

import argparse
import json
from typing import Any

from scrapy.exceptions import UsageError

from message_ingest.commands._common import run_graph


def dispatch_onedrive(command: Any, opts: argparse.Namespace) -> None:
    """Accept metadata pagination or an explicit set of content item IDs."""
    action = opts.resource_or_action
    if action not in {"discover", "delta", "content"}:
        raise UsageError("use 'microsoft onedrive {discover,delta,content}'")
    # Falsey values still mean the caller supplied an unrelated product option.
    # Boolean switches alone use False to represent absence.
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
    if action == "content" and opts.page_size is not None:
        used.append("page_size")
    if used:
        rendered = ", ".join(f"--{name.replace('_', '-')}" for name in used)
        raise UsageError(f"option(s) not valid for OneDrive {action}: {rendered}")

    if action == "content":
        item_ids = ([opts.action] if opts.action is not None else []) + opts.message_ids
        if not item_ids:
            raise UsageError("OneDrive content requires at least one ITEM_ID")
        if any(not value or value != value.strip() for value in item_ids):
            raise UsageError("ITEM_ID must be non-empty without surrounding whitespace")
        # JSON preserves commas and other ID characters until provider encoding.
        arguments = {"item_ids": json.dumps(list(dict.fromkeys(item_ids)))}
    else:
        if opts.action is not None or opts.message_ids:
            raise UsageError(f"OneDrive {action} does not accept ITEM_ID values")
        arguments = {"page_size": str(opts.page_size or 100)}
    run_graph(command, f"microsoft_onedrive_{action}", arguments)


__all__ = ["dispatch_onedrive"]
