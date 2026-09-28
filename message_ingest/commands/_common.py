"""Shared CLI validation and entry into Scrapy's native crawler process."""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from scrapy.exceptions import UsageError

if TYPE_CHECKING:
    from scrapy.commands import ScrapyCommand
    from scrapy.crawler import Crawler

logger = logging.getLogger(__name__)


def page_size(value: str) -> int:
    """Reject invalid Graph page sizes while argparse can report usage."""
    parsed = int(value)
    if not 1 <= parsed <= 1000:
        raise argparse.ArgumentTypeError("page size must be between 1 and 1000")
    return parsed


def non_negative_int(value: str) -> int:
    """Parse a nonnegative CLI limit; zero retains the caller's unlimited convention."""
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be >= 0")
    return parsed


def require_no_positional_args(args: list[str]) -> None:
    """Reject stray positionals before starting any crawl."""
    if args:
        raise UsageError("this command does not accept positional arguments")


def _crawler_failed(crawler: Crawler) -> bool:
    """Return failure facts published through stable crawler/spider contracts."""
    final_status = crawler.stats.get_value("msgloom/final/status")
    identity_gate_failed = bool(
        crawler.stats.get_value("msgloom/source_identity/gate_failed_count", 0)
    )
    spider_failed = bool(getattr(crawler.spider, "run_failed", False))
    return final_status == "failed" or identity_gate_failed or spider_failed


def run_graph(
    command: ScrapyCommand,
    spider_name: str,
    spider_args: dict[str, Any],
) -> Crawler:
    """Schedule one spider and propagate bootstrap/integrity failure to the CLI."""
    if (process := command.crawler_process) is None:
        raise RuntimeError(
            "Scrapy must initialize the crawler process before running a command"
        )
    crawler = process.create_crawler(spider_name)
    process.crawl(crawler, **spider_args)
    process.start()
    if process.bootstrap_failed or _crawler_failed(crawler):
        command.exitcode = 1
    return crawler


@dataclass(frozen=True, slots=True)
class GraphPhase:
    """One Scrapy crawl phase, its success gate, and optional follow-up planner."""

    spider_name: str
    spider_args: dict[str, Any]
    after: Callable[[Crawler], Iterable[GraphPhase]] | None = None
    accepted_final_statuses: frozenset[str] | None = None


def run_graph_workflow(
    command: ScrapyCommand,
    phases: Iterable[GraphPhase],
) -> tuple[Crawler, ...]:
    """Run dynamically planned Graph crawls sequentially in one reactor lifecycle.

    Every phase is a normal Scrapy crawler. Follow-up phases are created only
    after the preceding crawler has fully closed, so catalog writes are durable
    before planners read them. A failed phase stops the remaining workflow.
    """
    if (process := command.crawler_process) is None:
        raise RuntimeError(
            "Scrapy must initialize the crawler process before running a command"
        )

    pending = deque(phases)
    completed: list[Crawler] = []

    def schedule_next() -> None:
        if not pending or command.exitcode:
            return
        phase = pending.popleft()
        crawler = process.create_crawler(phase.spider_name)
        completed.append(crawler)
        handle = process.crawl(crawler, **phase.spider_args)

        def phase_finished(_result):
            final_status = crawler.stats.get_value("msgloom/final/status")
            status_rejected = (
                phase.accepted_final_statuses is not None
                and final_status not in phase.accepted_final_statuses
            )
            if process.bootstrap_failed or _crawler_failed(crawler) or status_rejected:
                command.exitcode = 1
                pending.clear()
                if status_rejected:
                    logger.error(
                        "Microsoft acquisition workflow phase did not reach an accepted "
                        "terminal status: spider=%s status=%s",
                        phase.spider_name,
                        final_status,
                    )
                return
            if phase.after is not None:
                try:
                    pending.extend(phase.after(crawler))
                except Exception as exc:  # noqa: BLE001 - command boundary must fail closed
                    command.exitcode = 1
                    pending.clear()
                    logger.error(
                        "Microsoft acquisition workflow planning failed: "
                        "spider=%s error_type=%s",
                        phase.spider_name,
                        type(exc).__name__,
                    )
                    return
            schedule_next()
            return

        def phase_failed(error) -> None:
            command.exitcode = 1
            pending.clear()
            failure_type = getattr(error, "type", None)
            if failure_type is not None:
                error_type = getattr(failure_type, "__name__", "UnknownError")
            elif isinstance(error, BaseException):
                error_type = type(error).__name__
            else:
                error_type = "UnknownError"
            logger.error(
                "Microsoft acquisition workflow phase failed: spider=%s error_type=%s",
                phase.spider_name,
                error_type,
            )

        add_callbacks = getattr(handle, "addCallbacks", None)
        if callable(add_callbacks):
            add_callbacks(phase_finished, phase_failed)
            return

        add_done_callback = getattr(handle, "add_done_callback", None)
        if callable(add_done_callback):

            def task_finished(task) -> None:
                if task.cancelled():
                    phase_failed(asyncio.CancelledError())
                    return
                error = task.exception()
                if error is not None:
                    phase_failed(error)
                    return
                phase_finished(None)

            add_done_callback(task_finished)
            return

        raise TypeError(
            "Scrapy crawler process returned an unsupported crawl completion handle"
        )

    schedule_next()
    process.start()
    if process.bootstrap_failed:
        command.exitcode = 1
    return tuple(completed)


__all__ = [
    "GraphPhase",
    "non_negative_int",
    "page_size",
    "require_no_positional_args",
    "run_graph",
    "run_graph_workflow",
]
