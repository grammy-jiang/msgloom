"""
Expose delta synchronization options; checkpoint ownership stays in the
extension.
"""

from __future__ import annotations

import argparse

from scrapy.commands import ScrapyCommand

from message_ingest.commands._common import (
    page_size,
    require_no_positional_args,
    run_graph,
)


class Command(ScrapyCommand):
    """
    Use native Scrapy help/options hooks and validate arguments before startup.
    """

    requires_project = True

    def syntax(self) -> str:
        return "[options]"

    def short_desc(self) -> str:
        return "Synchronize Outlook mailbox with Graph delta"

    def long_desc(self) -> str:
        return (
            "Run per-folder Outlook message delta synchronization using committed "
            "delta links and optional whole-mailbox reconciliation."
        )

    def add_options(self, parser: argparse.ArgumentParser) -> None:
        """
        Extend native Scrapy options with this acquisition mode's arguments.
        """
        super().add_options(parser)
        parser.add_argument(
            "--page-size",
            type=page_size,
            default=25,
            metavar="N",
            help="preferred Graph delta page size, 1..1000 (default: 25)",
        )
        parser.add_argument(
            "--reconcile",
            action=argparse.BooleanOptionalAction,
            default=True,
            help="enable whole-mailbox reconciliation (default: enabled)",
        )

    def run(self, args: list[str], opts: argparse.Namespace) -> None:
        """
        Validate input and start the named spider with serialized CLI values.
        """
        require_no_positional_args(args)
        run_graph(
            self,
            "outlook_delta",
            {
                "page_size": str(opts.page_size),
                "reconcile_global": "1" if opts.reconcile else "0",
            },
        )
