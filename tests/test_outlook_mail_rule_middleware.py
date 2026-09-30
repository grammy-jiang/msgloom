"""Scrapy adapter tests for Outlook Mail acquisition-rule middleware."""

from __future__ import annotations

import pytest
from scrapy.exceptions import NotConfigured
from scrapy.utils.test import get_crawler

from message_ingest.acquisition.microsoft.outlook.email.rule_evaluation import (
    MailRuleDecisionOutcome,
    MailRuleEvaluation,
    MailRuleEvaluationState,
    MailRuleObservation,
    MailRuleProbeData,
)
from message_ingest.spidermiddlewares.microsoft.outlook.email import (
    OutlookMailAcquisitionRuleMiddleware,
)
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)
from message_ingest.spiders.microsoft.outlook.email.full import OutlookFullSpider


class FakeEvaluator:
    def evaluate(
        self,
        observation: MailRuleObservation,
        *,
        probe: MailRuleProbeData | None = None,
    ) -> MailRuleEvaluation:
        del observation, probe
        return MailRuleEvaluation(
            state=MailRuleEvaluationState.FINAL,
            selected_profile="discovery-only",
            outcome=MailRuleDecisionOutcome.DEFAULT,
        )


class RuleEnabledDiscoverSpider(OutlookDiscoverSpider):
    @classmethod
    def build_mail_rule_evaluator(cls, crawler):
        del crawler
        return FakeEvaluator()


def _crawler_with_spider(spider_cls, **kwargs):
    crawler = get_crawler(spider_cls)
    spider = spider_cls.from_crawler(crawler, **kwargs)
    crawler.spider = spider
    return crawler, spider


def test_middleware_is_not_configured_without_collection_evaluator() -> None:
    crawler, _spider = _crawler_with_spider(OutlookDiscoverSpider)
    with pytest.raises(NotConfigured):
        OutlookMailAcquisitionRuleMiddleware.from_crawler(crawler)


def test_middleware_builds_for_collection_spider_with_evaluator() -> None:
    crawler, spider = _crawler_with_spider(RuleEnabledDiscoverSpider)
    middleware = OutlookMailAcquisitionRuleMiddleware.from_crawler(crawler)

    if middleware.spider is not spider:
        pytest.fail("Middleware must bind to the active Mail collection Spider")
    if middleware.evaluator is not spider.mail_rule_evaluator:
        pytest.fail("Middleware must consume the Spider-owned evaluator instance")


def test_middleware_rejects_non_collection_spider_even_if_misconfigured() -> None:
    crawler, _spider = _crawler_with_spider(
        OutlookFullSpider,
        message_ids="message-1",
    )
    with pytest.raises(NotConfigured):
        OutlookMailAcquisitionRuleMiddleware.from_crawler(crawler)


import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, cast

from scrapy.http import Request, Response

from message_ingest.items.microsoft.outlook.email import OutlookMailItem


class SequenceEvaluator:
    def __init__(self, evaluations: list[MailRuleEvaluation]) -> None:
        self._evaluations = iter(evaluations)
        self.calls: list[tuple[MailRuleObservation, MailRuleProbeData | None]] = []

    def evaluate(
        self,
        observation: MailRuleObservation,
        *,
        probe: MailRuleProbeData | None = None,
    ) -> MailRuleEvaluation:
        self.calls.append((observation, probe))
        return next(self._evaluations)


class ConfigurableDiscoverSpider(OutlookDiscoverSpider):
    configured_evaluator: SequenceEvaluator | None = None

    @classmethod
    def build_mail_rule_evaluator(cls, crawler):
        del crawler
        return cls.configured_evaluator


def _mail_item(message_id: str = "message-1") -> OutlookMailItem:
    return OutlookMailItem.from_graph(
        {
            "id": message_id,
            "subject": "private-subject",
            "from": {"emailAddress": {"address": "private@example.test"}},
            "lastModifiedDateTime": "2026-09-30T03:00:00Z",
        },
        source_response_url="https://graph.example.test/messages",
        observed_at="2026-09-30T03:00:01Z",
        observation_kind="delta",
        evidence_id=f"evidence-{message_id}",
        run_id="run-1",
    )


async def _outputs(*values: Any) -> AsyncIterator[Any]:
    for value in values:
        yield value


def _configured_middleware(evaluator: SequenceEvaluator):
    ConfigurableDiscoverSpider.configured_evaluator = evaluator
    crawler, spider = _crawler_with_spider(ConfigurableDiscoverSpider)
    return OutlookMailAcquisitionRuleMiddleware.from_crawler(crawler), spider


def _collect(middleware, *values: Any) -> list[Any]:
    async def collect() -> list[Any]:
        return [
            output
            async for output in middleware.process_spider_output(
                Response("https://example.test"),
                _outputs(*values),
            )
        ]

    return asyncio.run(collect())


def _final(profile: str, outcome: MailRuleDecisionOutcome) -> MailRuleEvaluation:
    return MailRuleEvaluation(
        state=MailRuleEvaluationState.FINAL,
        selected_profile=profile,
        outcome=outcome,
    )


def test_non_mail_outputs_pass_through_without_evaluator_call() -> None:
    evaluator = SequenceEvaluator([])
    middleware, _spider = _configured_middleware(evaluator)
    request = Request("https://example.test/request")
    ordinary_item = {"kind": "not-mail"}

    actual = _collect(middleware, request, ordinary_item)

    if actual != [request, ordinary_item]:
        pytest.fail("Non-Mail Spider output must pass through unchanged")
    if evaluator.calls:
        pytest.fail("Non-Mail Spider output must not invoke the Mail evaluator")


def test_mail_item_is_yielded_unchanged_before_final_policy_side_effects() -> None:
    evaluator = SequenceEvaluator(
        [_final("outlook-mail-full-v1", MailRuleDecisionOutcome.MATCHED)]
    )
    middleware, spider = _configured_middleware(evaluator)
    item = _mail_item()

    async def exercise() -> None:
        stream = middleware.process_spider_output(
            Response("https://example.test"),
            _outputs(item),
        )
        first = await anext(stream)
        if first is not item:
            pytest.fail(
                "Middleware must yield the exact original OutlookMailItem first"
            )
        if evaluator.calls:
            pytest.fail(
                "Policy evaluation must happen after the original Item is yielded"
            )
        if spider.mail_rule_profiles:
            pytest.fail("Runtime policy state must not precede the original Item")
        with pytest.raises(StopAsyncIteration):
            await anext(stream)

    asyncio.run(exercise())
    if len(evaluator.calls) != 1:
        pytest.fail("Mail Item must be evaluated exactly once after it passes through")


def test_final_profile_is_recorded_in_attempt_local_state() -> None:
    evaluator = SequenceEvaluator(
        [_final("outlook-mail-full-v1", MailRuleDecisionOutcome.MATCHED)]
    )
    middleware, spider = _configured_middleware(evaluator)
    item = _mail_item()

    actual = _collect(middleware, item)

    if actual != [item]:
        pytest.fail("FINAL evaluation must not emit an extra Spider output")
    if spider.mail_rule_profiles != (("message-1", "outlook-mail-full-v1"),):
        pytest.fail("FINAL profile must be retained in attempt-local Spider state")


def test_later_observation_overwrites_profile_for_same_message() -> None:
    evaluator = SequenceEvaluator(
        [
            _final("outlook-mail-full-v1", MailRuleDecisionOutcome.MATCHED),
            _final("discovery-only", MailRuleDecisionOutcome.DEFAULT),
        ]
    )
    middleware, spider = _configured_middleware(evaluator)
    first = _mail_item("message-1")
    second = _mail_item("message-1")

    actual = _collect(middleware, first, second)

    if actual != [first, second]:
        pytest.fail("Duplicate Mail observations must both remain source Items")
    if spider.mail_rule_profiles != (("message-1", "discovery-only"),):
        pytest.fail(
            "Latest evaluation must overwrite runtime profile without duplicate key"
        )


def test_process_spider_output_remains_streaming() -> None:
    evaluator = SequenceEvaluator(
        [
            _final("discovery-only", MailRuleDecisionOutcome.DEFAULT),
            _final("discovery-only", MailRuleDecisionOutcome.DEFAULT),
        ]
    )
    middleware, _spider = _configured_middleware(evaluator)
    first = _mail_item("message-1")
    second = _mail_item("message-2")
    second_requested = False

    async def source() -> AsyncIterator[OutlookMailItem]:
        nonlocal second_requested
        yield first
        second_requested = True
        yield second

    async def exercise() -> None:
        stream = cast(
            AsyncGenerator[Any, None],
            middleware.process_spider_output(
                Response("https://example.test"),
                source(),
            ),
        )
        output = await anext(stream)
        if output is not first:
            pytest.fail("First streamed Mail Item changed")
        if second_requested:
            pytest.fail("Middleware materialized or pre-consumed later Spider output")
        await stream.aclose()

    asyncio.run(exercise())


from message_ingest.acquisition.microsoft.outlook.email import (
    MailRuleProbeStatus,
    MailRuleRequiredData,
    OutlookMailRuleProbeResult,
    mail_rule_observation_from_item,
)


def _needs_body() -> MailRuleEvaluation:
    return MailRuleEvaluation(
        state=MailRuleEvaluationState.NEEDS_DATA,
        required_data=MailRuleRequiredData.BODY,
    )


def _complete_probe(item: OutlookMailItem) -> OutlookMailRuleProbeResult:
    observation = mail_rule_observation_from_item(item)
    return OutlookMailRuleProbeResult(
        observation=observation,
        probe=MailRuleProbeData(
            status=MailRuleProbeStatus.COMPLETE,
            body="complete body",
            last_modified_date_time="2026-09-30T03:00:00Z",
            evidence_id="probe-evidence",
        ),
    )


def test_needs_body_schedules_one_probe_after_original_item() -> None:
    evaluator = SequenceEvaluator([_needs_body()])
    middleware, _spider = _configured_middleware(evaluator)
    item = _mail_item()

    actual = _collect(middleware, item)

    if len(actual) != 2 or actual[0] is not item or not isinstance(actual[1], Request):
        pytest.fail("NEEDS_DATA must preserve Mail Item then emit one probe Request")
    if actual[1].callback != middleware.spider.parse_mail_rule_probe:
        pytest.fail("Middleware must delegate probe callback ownership to the Spider")


def test_multiple_needs_data_for_same_initial_observation_do_not_schedule_duplicate_probe() -> (
    None
):
    evaluator = SequenceEvaluator([_needs_body(), _needs_body()])
    middleware, _spider = _configured_middleware(evaluator)
    first = _mail_item()
    duplicate = _mail_item()

    actual = _collect(middleware, first, duplicate)

    requests = [output for output in actual if isinstance(output, Request)]
    items = [output for output in actual if isinstance(output, OutlookMailItem)]
    if len(requests) != 1:
        pytest.fail("Same observation must schedule at most one body probe")
    if items != [first, duplicate]:
        pytest.fail("Duplicate source observations must both pass through unchanged")


def test_probe_result_is_consumed_and_re_evaluated() -> None:
    evaluator = SequenceEvaluator(
        [
            _needs_body(),
            _final("outlook-mail-full-v1", MailRuleDecisionOutcome.MATCHED),
        ]
    )
    middleware, spider = _configured_middleware(evaluator)
    item = _mail_item()

    initial = _collect(middleware, item)
    if len(initial) != 2 or not isinstance(initial[1], Request):
        pytest.fail("Initial NEEDS_DATA did not schedule its probe")
    probe_result = _complete_probe(item)

    after_probe = _collect(middleware, probe_result)

    if after_probe:
        pytest.fail("Internal probe result must be consumed before Item Pipelines")
    if len(evaluator.calls) != 2 or evaluator.calls[1][1] != probe_result.probe:
        pytest.fail("Probe result must re-run the evaluator with bounded probe data")
    if spider.mail_rule_profiles != (("message-1", "outlook-mail-full-v1"),):
        pytest.fail("Terminal result after probe must update runtime profile state")


def test_needs_data_after_probe_marks_integrity_failure_instead_of_looping() -> None:
    evaluator = SequenceEvaluator([_needs_body(), _needs_body()])
    middleware, spider = _configured_middleware(evaluator)
    item = _mail_item()

    initial = _collect(middleware, item)
    if len(initial) != 2 or not isinstance(initial[1], Request):
        pytest.fail("Initial NEEDS_DATA did not schedule its probe")

    after_probe = _collect(middleware, _complete_probe(item))

    if after_probe:
        pytest.fail("Repeated NEEDS_DATA after probe must not emit another Request")
    if not spider.run_failed:
        pytest.fail(
            "Repeated NEEDS_DATA after supplied body must fail policy integrity"
        )
    if "mail_rule_probe_loop" not in spider.failure_reasons:
        pytest.fail("Probe-loop integrity failure reason changed")
