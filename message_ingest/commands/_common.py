"""Shared CLI validation and entry into Scrapy's native crawler process."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any

from scrapy.exceptions import UsageError

if TYPE_CHECKING:
    from scrapy.commands import ScrapyCommand


def page_size(value: str) -> int:
    """
    Reject invalid page sizes while argparse can still report a CLI usage
    error.
    """
    parsed = int(value)
    if not 1 <= parsed <= 1000:
        raise argparse.ArgumentTypeError("page size must be between 1 and 1000")
    return parsed


def non_negative_int(value: str) -> int:
    """
    Parse a nonnegative CLI limit; zero retains the caller's unlimited
    convention.
    """
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return parsed


def require_no_positional_args(args: list[str]) -> None:
    """Reject stray positionals before starting any crawl."""
    if args:
        raise UsageError("this command does not accept positional arguments")


def run_outlook(
    command: ScrapyCommand, spider_name: str, spider_args: dict[str, Any]
) -> None:
    """
    Schedule the selected spider once and propagate bootstrap failure to the
    CLI exit code.
    """
    if (process := command.crawler_process) is None:
        raise RuntimeError(
            "Scrapy must initialize the crawler process before running a command"
        )
    crawler = process.create_crawler(spider_name)
    process.crawl(crawler, **spider_args)
    process.start()
    if process.bootstrap_failed:
        command.exitcode = 1
        return
    final_status = crawler.stats.get_value("msgloom/final/status")
    identity_gate_failed = bool(
        crawler.stats.get_value("msgloom/source_identity/gate_failed_count", 0)
    )
    spider_failed = bool(getattr(crawler.spider, "run_failed", False))
    if final_status == "failed" or identity_gate_failed or spider_failed:
        command.exitcode = 1
