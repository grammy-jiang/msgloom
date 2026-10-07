"""Microsoft account profile command dispatch."""

from __future__ import annotations

import argparse
import json
from typing import Any

from message_ingest.commands._common import run_graph
from message_ingest.commands.microsoft.validation import (
    reject_options,
    require_profile_path,
)


def dispatch_profile(command: Any, opts: argparse.Namespace) -> None:
    """Run profile acquisition through the shared Scrapy Graph lifecycle."""
    require_profile_path(opts)
    reject_options(opts, allowed=set())
    crawler = run_graph(command, "microsoft_profile", {})
    if command.exitcode:
        return

    profile = getattr(crawler.spider, "profile", None)
    stats = crawler.stats
    evidence_ready = int(
        stats.get_value("msgloom/evidence/response_persisted_count", 0) or 0
    ) + int(stats.get_value("msgloom/evidence/cache_link_count", 0) or 0)
    if not isinstance(profile, dict) or evidence_ready != 1:
        command.exitcode = 1
        return
    print(json.dumps(profile, ensure_ascii=False, sort_keys=True))


__all__ = ["dispatch_profile"]
