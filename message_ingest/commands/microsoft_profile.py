"""Print the signed-in Microsoft Graph user profile as JSON."""

from __future__ import annotations

import argparse
import json

from scrapy.commands import ScrapyCommand

from message_ingest.commands._common import require_no_positional_args, run_graph


class Command(ScrapyCommand):
    """Run the one-shot profile spider through the normal Scrapy lifecycle."""

    requires_project = True

    def syntax(self) -> str:
        return "[options]"

    def short_desc(self) -> str:
        return "Get the signed-in Microsoft Graph user profile"

    def long_desc(self) -> str:
        return (
            "Fetch Microsoft Graph /me with User.Read through the shared "
            "authentication, retry, diagnostics, source-identity, and raw-"
            "evidence lifecycle, then print the profile JSON."
        )

    def add_options(self, parser: argparse.ArgumentParser) -> None:
        """Retain the standard Scrapy command options."""
        super().add_options(parser)

    def run(self, args: list[str], opts: argparse.Namespace) -> None:
        """Run one profile request and print only a validated profile result."""
        del opts
        require_no_positional_args(args)
        crawler = run_graph(self, "microsoft_profile", {})
        if self.exitcode:
            return

        profile = getattr(crawler.spider, "profile", None)
        stats = crawler.stats
        evidence_ready = int(
            stats.get_value("msgloom/evidence/response_persisted_count", 0) or 0
        ) + int(stats.get_value("msgloom/evidence/cache_link_count", 0) or 0)
        if not isinstance(profile, dict) or evidence_ready != 1:
            self.exitcode = 1
            return
        print(json.dumps(profile, ensure_ascii=False, sort_keys=True))
