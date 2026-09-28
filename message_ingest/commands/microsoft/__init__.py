"""Single public namespace for Microsoft acquisition and authentication."""

from __future__ import annotations

import argparse

from scrapy.commands import ScrapyCommand
from scrapy.exceptions import UsageError

from message_ingest.commands._common import require_no_positional_args
from message_ingest.commands.microsoft.auth import dispatch_auth
from message_ingest.commands.microsoft.options import add_microsoft_options
from message_ingest.commands.microsoft.outlook import dispatch_outlook
from message_ingest.commands.microsoft.profile import dispatch_profile


class Command(ScrapyCommand):
    """Expose every Microsoft product below one public command namespace."""

    requires_project = True
    requires_crawler_process = True

    def syntax(self) -> str:
        return (
            "{profile,auth,outlook} [RESOURCE_OR_ACTION] [ACTION] "
            "[RESOURCE_ID ...] [options]"
        )

    def short_desc(self) -> str:
        return "Manage Microsoft acquisition and authentication"

    def long_desc(self) -> str:
        return (
            "Use one Microsoft namespace for account profile, authentication "
            "management, and Outlook Mail/Calendar acquisition. Operations that "
            "need Microsoft authentication run through the normal Scrapy Graph "
            "lifecycle."
        )

    def add_options(self, parser: argparse.ArgumentParser) -> None:
        super().add_options(parser)
        add_microsoft_options(self, parser)

    def run(self, args: list[str], opts: argparse.Namespace) -> None:
        """Dispatch the selected Microsoft hierarchy path."""
        require_no_positional_args(args)
        if opts.section == "profile":
            dispatch_profile(self, opts)
            return
        if opts.section == "auth":
            dispatch_auth(self, opts)
            return
        if opts.section == "outlook":
            dispatch_outlook(self, opts)
            return
        raise UsageError("unsupported Microsoft command path")


__all__ = ["Command"]
