"""Expose Calendar inventory options without duplicating spider traversal."""

from __future__ import annotations

import argparse

from scrapy.commands import ScrapyCommand

from message_ingest.commands._common import (
    page_size,
    require_no_positional_args,
    run_graph,
)


class Command(ScrapyCommand):
    """Map Calendar inventory CLI options to the native Scrapy spider."""

    requires_project = True

    def syntax(self) -> str:
        return "[options]"

    def short_desc(self) -> str:
        return "Discover Microsoft calendars"

    def add_options(self, parser: argparse.ArgumentParser) -> None:
        """Add bounded Calendar inventory options."""
        super().add_options(parser)
        parser.add_argument(
            "--page-size",
            type=page_size,
            default=100,
            metavar="N",
            help="Graph page size, 1..1000 (default: 100)",
        )

    def run(self, args: list[str], opts: argparse.Namespace) -> None:
        """Validate arguments and schedule Calendar discovery once."""
        require_no_positional_args(args)
        run_graph(
            self,
            "outlook_calendar_discover",
            {"page_size": str(opts.page_size)},
        )
