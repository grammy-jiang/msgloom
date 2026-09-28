"""Outlook Mail command dispatch."""

from __future__ import annotations

import argparse
from typing import Any

from scrapy.exceptions import UsageError

from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.commands._common import run_graph
from message_ingest.commands.microsoft.outlook.sync import run_mail_sync
from message_ingest.commands.microsoft.validation import reject_options


def dispatch_mail(command: Any, opts: argparse.Namespace) -> None:
    """Map Outlook Mail actions to their existing spiders."""
    if opts.action == "discover":
        if opts.message_ids:
            raise UsageError("Mail discover does not accept MESSAGE_ID values")
        reject_options(opts, allowed={"folder", "page_size", "max_pages"})
        run_graph(
            command,
            "outlook_discover",
            {
                "folder": opts.folder or "",
                "page_size": str(opts.page_size or 25),
                "max_pages": str(0 if opts.max_pages is None else opts.max_pages),
            },
        )
        return
    if opts.action == "delta":
        if opts.message_ids:
            raise UsageError("Mail delta does not accept MESSAGE_ID values")
        reject_options(opts, allowed={"page_size", "reconcile"})
        reconcile = True if opts.reconcile is None else opts.reconcile
        run_graph(
            command,
            "outlook_delta",
            {
                "page_size": str(opts.page_size or 25),
                "reconcile_global": "1" if reconcile else "0",
            },
        )
        return
    if opts.action == "sync":
        if opts.message_ids:
            raise UsageError("Mail sync does not accept MESSAGE_ID values")
        reject_options(opts, allowed={"page_size", "reconcile", "max_enrich"})
        run_mail_sync(command, opts)
        return
    if opts.action == "full":
        reject_options(opts, allowed={"operation", "acquisition_profile"})
        message_ids = tuple(
            dict.fromkeys(
                cleaned for value in opts.message_ids if (cleaned := value.strip())
            )
        )
        if not message_ids:
            raise UsageError("at least one MESSAGE_ID is required")
        profile = opts.acquisition_profile or FULL_V1
        if profile != FULL_V1:
            raise UsageError("Mail full requires the Outlook Mail acquisition profile")
        run_graph(
            command,
            "outlook_full",
            {
                "message_ids": ",".join(message_ids),
                "operation": opts.operation or "refresh",
                "profile": profile,
            },
        )
        return
    raise UsageError("use 'microsoft outlook mail {discover,delta,full,sync}'")


__all__ = ["dispatch_mail"]
