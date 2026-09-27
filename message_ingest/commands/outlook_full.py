"""
Map targeted message IDs and profile choices to the full acquisition spider.
"""

from __future__ import annotations

import argparse

from scrapy.commands import ScrapyCommand
from scrapy.exceptions import UsageError

from message_ingest.commands._common import run_graph
from message_ingest.profiles import FULL_V1


class Command(ScrapyCommand):
    """
    Use native Scrapy help/options hooks and validate arguments before startup.
    """

    requires_project = True

    def syntax(self) -> str:
        return "[options] MESSAGE_ID [MESSAGE_ID ...]"

    def short_desc(self) -> str:
        return "Acquire full Outlook message surfaces"

    def long_desc(self) -> str:
        return (
            "Run targeted Outlook Full acquisition for one or more message IDs. "
            "Refresh reacquires all Full-profile surfaces; enrich requests only "
            "surfaces that are not already terminal in the local catalog."
        )

    def add_options(self, parser: argparse.ArgumentParser) -> None:
        """
        Extend native Scrapy options with this acquisition mode's arguments.
        """
        super().add_options(parser)
        parser.add_argument(
            "--operation",
            choices=("enrich", "refresh"),
            default="refresh",
            help="enrich missing surfaces or refresh all surfaces (default: refresh)",
        )
        parser.add_argument(
            "--acquisition-profile",
            dest="acquisition_profile",
            choices=(FULL_V1,),
            default=FULL_V1,
            help=f"acquisition profile (default: {FULL_V1})",
        )

    def run(self, args: list[str], opts: argparse.Namespace) -> None:
        """
        Validate input and start the named spider with serialized CLI values.
        """
        message_ids = tuple(
            dict.fromkeys(cleaned for value in args if (cleaned := value.strip()))
        )
        if not message_ids:
            raise UsageError("at least one MESSAGE_ID is required")
        run_graph(
            self,
            "outlook_full",
            {
                "message_ids": ",".join(message_ids),
                "operation": opts.operation,
                "profile": opts.acquisition_profile,
            },
        )
