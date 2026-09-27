"""Expose bounded Calendar-view acquisition through a thin Scrapy command."""

from __future__ import annotations

import argparse
from datetime import datetime

from scrapy.commands import ScrapyCommand
from scrapy.exceptions import UsageError

from message_ingest.commands._common import (
    page_size,
    require_no_positional_args,
    run_graph,
)


def _aware_datetime(value: str) -> str:
    """Require a timezone-aware ISO-8601 datetime while preserving text."""
    cleaned = value.strip()
    if cleaned != value or not cleaned:
        raise argparse.ArgumentTypeError(
            "datetime must be non-empty with no surrounding whitespace"
        )
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "datetime must be valid ISO-8601"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("datetime must include a timezone offset")
    return cleaned


def _parsed(value: str) -> datetime:
    """Parse a value already validated by :func:`_aware_datetime`."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Command(ScrapyCommand):
    """Map one declared Calendar window to the native Scrapy spider."""

    requires_project = True

    def syntax(self) -> str:
        return "[options]"

    def short_desc(self) -> str:
        return "Acquire a Microsoft Calendar time window"

    def add_options(self, parser: argparse.ArgumentParser) -> None:
        """Add explicit time-range and calendar-selection arguments."""
        super().add_options(parser)
        parser.add_argument(
            "--start",
            required=True,
            type=_aware_datetime,
            metavar="ISO_DATETIME",
            help="inclusive Calendar window start with timezone offset",
        )
        parser.add_argument(
            "--end",
            required=True,
            type=_aware_datetime,
            metavar="ISO_DATETIME",
            help="Calendar window end with timezone offset",
        )
        parser.add_argument(
            "--calendar",
            default="",
            metavar="CALENDAR_ID",
            help="specific calendar ID; empty selects the default calendar",
        )
        parser.add_argument(
            "--page-size",
            type=page_size,
            default=100,
            metavar="N",
            help="Graph page size, 1..1000 (default: 100)",
        )

    def run(self, args: list[str], opts: argparse.Namespace) -> None:
        """Validate the window and schedule one Calendar-view crawl."""
        require_no_positional_args(args)
        if _parsed(opts.start) >= _parsed(opts.end):
            raise UsageError("--start must be earlier than --end")
        run_graph(
            self,
            "outlook_calendar_window",
            {
                "start_datetime": opts.start,
                "end_datetime": opts.end,
                "calendar_id": opts.calendar,
                "page_size": str(opts.page_size),
            },
        )
