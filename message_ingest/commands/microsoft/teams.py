"""Dispatch delegated Teams discovery through the native Scrapy lifecycle."""

import argparse

from scrapy.commands import ScrapyCommand
from scrapy.exceptions import UsageError

from message_ingest.commands import _common


def dispatch_teams(command: ScrapyCommand, opts: argparse.Namespace) -> None:
    """
    Select full chat or channel discovery without changing spider defaults.

    Only the selected delegated T1/T2 surfaces are exposed. Native settings
    retain their normal priority. Resource limits, date windows, and resume
    are not command modes; reject unrelated flags instead of ignoring them.
    """
    resource = opts.resource_or_action
    if resource not in {"chat", "channel"} or opts.action != "discover":
        raise UsageError("use 'microsoft teams {chat,channel} discover'")
    if opts.message_ids:
        raise UsageError("Teams discovery does not accept RESOURCE_ID values")
    if command.settings is not None and command.settings.get("JOBDIR"):
        raise UsageError("Teams discovery does not support JOBDIR")
    used = [
        name
        for name in (
            "page_size",
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
        raise UsageError(f"option(s) not valid for Teams discovery: {rendered}")
    _common.run_graph(command, f"microsoft_teams_{resource}_discover", {})


__all__ = ["dispatch_teams"]
