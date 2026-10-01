"""Verify sequential dynamic Scrapy workflow orchestration."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from scrapy.commands import ScrapyCommand
from twisted.internet.defer import succeed

from message_ingest.commands._common import GraphPhase, run_graph_workflow


class FakeStats:
    def __init__(self, final_status: str | None = None) -> None:
        self.final_status = final_status

    def get_value(self, key: str, default=None):
        if key == "msgloom/final/status":
            return self.final_status
        return default


class FakeCrawler:
    def __init__(self, name: str) -> None:
        self.name = name
        self.stats = FakeStats()
        self.spider = SimpleNamespace(run_failed=False, run_id=f"run-{name}")


class FakeProcess:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.bootstrap_failed = False
        self.started = False

    @staticmethod
    def create_crawler(name: str) -> FakeCrawler:
        return FakeCrawler(name)

    def crawl(self, crawler: FakeCrawler, **kwargs):
        self.calls.append((crawler.name, kwargs))
        return succeed(None)

    def start(self) -> None:
        self.started = True


def test_workflow_appends_dynamic_phases_sequentially() -> None:
    process = FakeProcess()
    command = cast(ScrapyCommand, SimpleNamespace(crawler_process=process, exitcode=0))

    def after_first(_crawler):
        return [GraphPhase("second", {"value": 2})]

    crawlers = run_graph_workflow(
        command,
        [GraphPhase("first", {"value": 1}, after=after_first)],
    )

    if process.calls != [("first", {"value": 1}), ("second", {"value": 2})]:
        pytest.fail(f"Unexpected dynamic workflow order: {process.calls!r}")
    if [getattr(crawler, "name", None) for crawler in crawlers] != [
        "first",
        "second",
    ]:
        pytest.fail("Expected both workflow crawlers to be retained")
    if not process.started or command.exitcode != 0:
        pytest.fail("Expected successful workflow process lifecycle")


def test_workflow_stops_after_failed_phase() -> None:
    process = FakeProcess()
    command = cast(ScrapyCommand, SimpleNamespace(crawler_process=process, exitcode=0))

    def create_failed(name: str) -> FakeCrawler:
        crawler = FakeCrawler(name)
        if name == "first":
            crawler.spider.run_failed = True
        return crawler

    process.create_crawler = create_failed  # type: ignore[method-assign]
    run_graph_workflow(
        command,
        [GraphPhase("first", {}, after=lambda _crawler: [GraphPhase("second", {})])],
    )

    if process.calls != [("first", {})]:
        pytest.fail("Expected failed workflow phase to stop follow-up crawlers")
    if command.exitcode != 1:
        pytest.fail("Expected failed workflow phase to set exit code 1")


def test_workflow_can_require_specific_terminal_status() -> None:
    process = FakeProcess()
    command = cast(ScrapyCommand, SimpleNamespace(crawler_process=process, exitcode=0))

    crawler = FakeCrawler("first")
    crawler.stats = FakeStats("incomplete")
    process.create_crawler = lambda _name: crawler  # type: ignore[method-assign]

    run_graph_workflow(
        command,
        [
            GraphPhase(
                "first",
                {},
                after=lambda _crawler: [GraphPhase("second", {})],
                accepted_final_statuses=frozenset({"completed"}),
            )
        ],
    )

    if process.calls != [("first", {})]:
        pytest.fail("Expected rejected terminal status to stop workflow")
    if command.exitcode != 1:
        pytest.fail("Expected rejected terminal status to fail workflow")


def test_phase_completion_validator_overrides_generic_spider_failure_gate() -> None:
    process = FakeProcess()
    command = cast(ScrapyCommand, SimpleNamespace(crawler_process=process, exitcode=0))

    def create_failed(name: str) -> FakeCrawler:
        crawler = FakeCrawler(name)
        crawler.spider.run_failed = name == "first"
        return crawler

    process.create_crawler = create_failed  # type: ignore[method-assign]
    seen: list[str] = []

    run_graph_workflow(
        command,
        [
            GraphPhase(
                "first",
                {},
                completion_validator=lambda crawler: (
                    seen.append(cast(FakeCrawler, crawler).name) or True
                ),
                after=lambda _crawler: [GraphPhase("second", {})],
            )
        ],
    )

    if seen != ["first"]:
        pytest.fail(f"Phase validator did not run exactly once: {seen!r}")
    if process.calls != [("first", {}), ("second", {})]:
        pytest.fail("Accepted custom completion gate did not allow follow-up phase")
    if command.exitcode != 0:
        pytest.fail("Accepted custom completion gate incorrectly failed workflow")


@pytest.mark.parametrize("mode", ("false", "raise"))
def test_phase_completion_validator_rejection_stops_workflow(mode: str) -> None:
    process = FakeProcess()
    command = cast(ScrapyCommand, SimpleNamespace(crawler_process=process, exitcode=0))

    def validator(_crawler):
        if mode == "raise":
            raise RuntimeError("private validator failure")
        return False

    run_graph_workflow(
        command,
        [
            GraphPhase(
                "first",
                {},
                completion_validator=validator,
                after=lambda _crawler: [GraphPhase("second", {})],
            )
        ],
    )

    if process.calls != [("first", {})] or command.exitcode != 1:
        pytest.fail("Rejected completion validator did not stop workflow")


def test_bootstrap_failure_remains_fatal_with_custom_completion_validator() -> None:
    process = FakeProcess()
    process.bootstrap_failed = True
    command = cast(ScrapyCommand, SimpleNamespace(crawler_process=process, exitcode=0))
    called = False

    def validator(_crawler):
        nonlocal called
        called = True
        return True

    run_graph_workflow(
        command,
        [GraphPhase("first", {}, completion_validator=validator)],
    )

    if called:
        pytest.fail("Bootstrap failure must abort before custom completion validator")
    if command.exitcode != 1:
        pytest.fail("Bootstrap failure did not fail custom-gated workflow")


def test_workflow_on_success_runs_once_after_dynamic_phases() -> None:
    process = FakeProcess()
    command = cast(ScrapyCommand, SimpleNamespace(crawler_process=process, exitcode=0))
    calls: list[tuple[str, ...]] = []

    run_graph_workflow(
        command,
        [
            GraphPhase(
                "first",
                {},
                after=lambda _crawler: [GraphPhase("second", {})],
            )
        ],
        on_success=lambda crawlers: calls.append(
            tuple(cast(FakeCrawler, crawler).name for crawler in crawlers)
        ),
    )

    if calls != [("first", "second")]:
        pytest.fail(f"Workflow on_success cardinality/order changed: {calls!r}")


def test_workflow_on_success_runs_for_zero_phase_workflow() -> None:
    process = FakeProcess()
    command = cast(ScrapyCommand, SimpleNamespace(crawler_process=process, exitcode=0))
    calls: list[tuple[object, ...]] = []

    run_graph_workflow(
        command,
        [],
        on_success=lambda crawlers: calls.append(crawlers),
    )

    if calls != [()]:
        pytest.fail("Zero-phase workflow did not finalize exactly once")


def test_workflow_on_success_failure_sets_exitcode() -> None:
    process = FakeProcess()
    command = cast(ScrapyCommand, SimpleNamespace(crawler_process=process, exitcode=0))

    def fail(_crawlers):
        raise RuntimeError("private finalizer error")

    run_graph_workflow(
        command,
        [GraphPhase("first", {})],
        on_success=fail,
    )

    if command.exitcode != 1:
        pytest.fail("Workflow finalizer failure did not fail command")
