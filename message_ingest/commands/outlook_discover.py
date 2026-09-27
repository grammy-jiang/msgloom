"""Expose discovery options without duplicating spider traversal."""

from __future__ import annotations

import argparse

from scrapy.commands import ScrapyCommand

from message_ingest.commands._common import (
    non_negative_int,
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
        return "Discover Outlook mailbox messages"

    def long_desc(self) -> str:
        return (
            "Run Outlook mailbox discovery with Graph pagination. By default the "
            "entire mailbox is scanned; --folder restricts discovery to one folder."
        )

    def add_options(self, parser: argparse.ArgumentParser) -> None:
        """
        Extend native Scrapy options with this acquisition mode's arguments.
        """
        super().add_options(parser)
        parser.add_argument(
            "--folder",
            default="",
            metavar="FOLDER_ID",
            help="discover one Graph mail folder instead of the whole mailbox",
        )
        parser.add_argument(
            "--page-size",
            type=page_size,
            default=25,
            metavar="N",
            help="Graph page size, 1..1000 (default: 25)",
        )
        parser.add_argument(
            "--max-pages",
            type=non_negative_int,
            default=0,
            metavar="N",
            help="stop after N pages; 0 means unlimited (default: 0)",
        )

    def run(self, args: list[str], opts: argparse.Namespace) -> None:
        """
        Validate input and start the named spider with serialized CLI values.
        """
        require_no_positional_args(args)
        run_graph(
            self,
            "outlook_discover",
            {
                "folder": opts.folder,
                "page_size": str(opts.page_size),
                "max_pages": str(opts.max_pages),
            },
        )
