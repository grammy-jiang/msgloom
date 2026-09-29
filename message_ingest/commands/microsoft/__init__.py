"""Single public namespace for Microsoft acquisition and authentication."""

from __future__ import annotations

import argparse

from scrapy.commands import ScrapyCommand
from scrapy.exceptions import UsageError

from message_ingest.commands._common import require_no_positional_args
from message_ingest.commands.microsoft.auth import dispatch_auth
from message_ingest.commands.microsoft.contacts import dispatch_contacts
from message_ingest.commands.microsoft.onedrive import dispatch_onedrive
from message_ingest.commands.microsoft.options import add_microsoft_options
from message_ingest.commands.microsoft.outlook import dispatch_outlook
from message_ingest.commands.microsoft.profile import dispatch_profile
from message_ingest.commands.microsoft.todo import dispatch_todo


class Command(ScrapyCommand):
    """Expose every Microsoft product below one public command namespace."""

    requires_project = True
    requires_crawler_process = True

    def syntax(self) -> str:
        return (
            "{profile,auth,outlook,todo,onedrive,contacts} [RESOURCE_OR_ACTION] [ACTION] "
            "[RESOURCE_ID ...] [options]"
        )

    def short_desc(self) -> str:
        return "Manage Microsoft acquisition and authentication"

    def long_desc(self) -> str:
        return (
            "Use one Microsoft namespace for account profile, authentication "
            "management, Outlook Mail/Calendar, To Do, OneDrive, and Contacts acquisition. "
            "Operations that "
            "need Microsoft authentication run through the normal Scrapy Graph "
            "lifecycle."
        )

    def add_options(self, parser: argparse.ArgumentParser) -> None:
        super().add_options(parser)
        add_microsoft_options(self, parser)

    def process_options(self, args: list[str], opts: argparse.Namespace) -> None:
        """Apply Outlook mailbox targeting before CrawlerProcess construction."""
        super().process_options(args, opts)
        mailbox = getattr(opts, "mailbox", None)
        if mailbox is None:
            return
        if not isinstance(mailbox, str) or not mailbox or mailbox != mailbox.strip():
            raise UsageError(
                "--mailbox must be non-empty without surrounding whitespace"
            )
        if self.settings is None:
            raise RuntimeError("Scrapy did not initialize command settings")
        self.settings.set("MSGLOOM_TARGET_MAILBOX", mailbox, priority="cmdline")

    def run(self, args: list[str], opts: argparse.Namespace) -> None:
        """Dispatch the selected Microsoft hierarchy path."""
        require_no_positional_args(args)
        if getattr(opts, "mailbox", None) is not None and opts.section != "outlook":
            raise UsageError("--mailbox is valid only below 'microsoft outlook'")
        if opts.section == "profile":
            dispatch_profile(self, opts)
            return
        if opts.section == "auth":
            dispatch_auth(self, opts)
            return
        if opts.section == "outlook":
            dispatch_outlook(self, opts)
            return
        if opts.section == "todo":
            dispatch_todo(self, opts)
            return
        if opts.section == "onedrive":
            dispatch_onedrive(self, opts)
            return
        if opts.section == "contacts":
            dispatch_contacts(self, opts)
            return
        raise UsageError("unsupported Microsoft command path")


__all__ = ["Command"]
