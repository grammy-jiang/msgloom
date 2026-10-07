"""Outlook Calendar command dispatch."""

from __future__ import annotations

import argparse
from typing import Any

from scrapy.exceptions import UsageError

from message_ingest.acquisition.microsoft.outlook.calendar.profile import (
    FULL_V1 as CALENDAR_FULL_V1,
)
from message_ingest.commands._common import run_graph
from message_ingest.commands.microsoft.outlook.sync import run_calendar_sync
from message_ingest.commands.microsoft.validation import reject_options
from microsoft_graph.protocol.calendar import calendar_window


def dispatch_calendar(command: Any, opts: argparse.Namespace) -> None:
    """Validate one Calendar action and map it to its internal spider."""
    if opts.calendar is not None and (
        not opts.calendar or opts.calendar != opts.calendar.strip()
    ):
        raise UsageError("--calendar must be non-empty without surrounding whitespace")
    if opts.action == "discover":
        if opts.message_ids:
            raise UsageError("Calendar discover does not accept RESOURCE_ID values")
        reject_options(opts, allowed={"page_size"})
        run_graph(
            command,
            "outlook_calendar_discover",
            {"page_size": str(opts.page_size or 100)},
        )
        return
    if opts.action == "window":
        if opts.message_ids:
            raise UsageError("Calendar window does not accept RESOURCE_ID values")
        reject_options(opts, allowed={"start", "end", "calendar", "page_size"})
        _require_window(opts, action="window")
        run_graph(
            command,
            "outlook_calendar_window",
            {
                "start_datetime": opts.start,
                "end_datetime": opts.end,
                "calendar_id": opts.calendar or "",
                "page_size": str(opts.page_size or 100),
            },
        )
        return
    if opts.action == "delta":
        if opts.message_ids:
            raise UsageError("Calendar delta does not accept RESOURCE_ID values")
        reject_options(opts, allowed={"start", "end", "page_size"})
        _require_window(opts, action="delta")
        run_graph(
            command,
            "outlook_calendar_delta",
            {
                "start_datetime": opts.start,
                "end_datetime": opts.end,
                "page_size": str(opts.page_size or 100),
            },
        )
        return
    if opts.action == "sync":
        if opts.message_ids:
            raise UsageError("Calendar sync does not accept RESOURCE_ID values")
        reject_options(opts, allowed={"start", "end", "page_size", "max_enrich"})
        _require_window(opts, action="sync")
        run_calendar_sync(command, opts)
        return
    if opts.action == "full":
        reject_options(
            opts,
            allowed={"calendar", "page_size", "operation", "acquisition_profile"},
        )
        event_ids = tuple(
            dict.fromkeys(
                cleaned for value in opts.message_ids if (cleaned := value.strip())
            )
        )
        if not event_ids:
            raise UsageError("at least one EVENT_ID is required")
        profile = opts.acquisition_profile or CALENDAR_FULL_V1
        if profile != CALENDAR_FULL_V1:
            raise UsageError(
                "Calendar full requires the Outlook Calendar acquisition profile"
            )
        run_graph(
            command,
            "outlook_calendar_full",
            {
                "event_ids": list(event_ids),
                "calendar_id": opts.calendar or "",
                "page_size": str(opts.page_size or 100),
                "operation": opts.operation or "refresh",
                "profile": profile,
            },
        )
        return
    raise UsageError(
        "use 'microsoft outlook calendar {discover,window,delta,full,sync}'"
    )


def _require_window(opts: argparse.Namespace, *, action: str) -> None:
    if opts.start is None or opts.end is None:
        raise UsageError(f"calendar {action} requires --start and --end")
    try:
        calendar_window(opts.start, opts.end)
    except ValueError as exc:
        message = (
            str(exc)
            .replace("start_datetime", "--start")
            .replace("end_datetime", "--end")
        )
        raise UsageError(message) from exc


__all__ = ["dispatch_calendar"]
