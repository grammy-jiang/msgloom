"""Privacy-safe logging, stats, and integrity for Mail rule middleware."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import pytest
from scrapy.http import Response
from scrapy.utils.test import get_crawler

from message_ingest.acquisition.microsoft.outlook.email import (
    MailRuleDecisionOutcome,
    MailRuleEvaluation,
    MailRuleEvaluationState,
    MailRuleObservation,
    MailRuleProbeData,
    MailRuleProbeStatus,
    MailRuleRequiredData,
    OutlookMailRuleProbeResult,
    mail_rule_observation_from_item,
)
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.spidermiddlewares.microsoft.outlook.email import (
    OutlookMailAcquisitionRuleMiddleware,
)
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)

LOGGER = "message_ingest.spidermiddlewares.microsoft.outlook.email"
PRIVATE_EXCEPTION = "private-exception-message-never-log"
PRIVATE_SUBJECT = "private-subject-never-log"
PRIVATE_BODY = "private-body-never-log"
PRIVATE_ADDRESS = "private-address-never-log@example.test"


class QueueEvaluator:
    def __init__(self, values: list[MailRuleEvaluation]) -> None:
        self.values = iter(values)

    def evaluate(
        self,
        observation: MailRuleObservation,
        *,
        probe: MailRuleProbeData | None = None,
    ) -> MailRuleEvaluation:
        del observation, probe
        return next(self.values)


class RaisingEvaluator:
    def evaluate(
        self,
        observation: MailRuleObservation,
        *,
        probe: MailRuleProbeData | None = None,
    ) -> MailRuleEvaluation:
        del observation, probe
        raise RuntimeError(PRIVATE_EXCEPTION)


class ObservableDiscoverSpider(OutlookDiscoverSpider):
    configured_evaluator: Any = None

    @classmethod
    def build_mail_rule_evaluator(cls, crawler):
        del crawler
        return cls.configured_evaluator


def _middleware(evaluator):
    ObservableDiscoverSpider.configured_evaluator = evaluator
    crawler = get_crawler(ObservableDiscoverSpider)
    spider = ObservableDiscoverSpider.from_crawler(crawler)
    crawler.spider = spider
    return OutlookMailAcquisitionRuleMiddleware.from_crawler(crawler), spider


def _item() -> OutlookMailItem:
    return OutlookMailItem.from_graph(
        {
            "id": "message-1",
            "subject": PRIVATE_SUBJECT,
            "sender": {"emailAddress": {"address": PRIVATE_ADDRESS}},
            "from": {"emailAddress": {"address": PRIVATE_ADDRESS}},
            "toRecipients": [{"emailAddress": {"address": PRIVATE_ADDRESS}}],
            "bodyPreview": PRIVATE_BODY,
            "lastModifiedDateTime": "2026-09-30T03:00:00Z",
        },
        source_response_url="https://graph.example.test/messages?private=url",
        observed_at="2026-09-30T03:00:01Z",
        observation_kind="delta",
        evidence_id="evidence-1",
        run_id="run-1",
    )


async def _outputs(*values: Any) -> AsyncIterator[Any]:
    for value in values:
        yield value


def _collect(middleware, *values: Any) -> list[Any]:
    async def collect() -> list[Any]:
        return [
            value
            async for value in middleware.process_spider_output(
                Response("https://example.test"),
                _outputs(*values),
            )
        ]

    return asyncio.run(collect())


def _matched(*, probe_used: bool = False) -> MailRuleEvaluation:
    return MailRuleEvaluation(
        state=MailRuleEvaluationState.FINAL,
        selected_profile="outlook-mail-full-v1",
        outcome=MailRuleDecisionOutcome.MATCHED,
        ruleset_id="ruleset-1",
        ruleset_digest="a" * 64,
        matched_rule_ids=("r1", "r2"),
        stop_rule_id="r2",
        probe_used=probe_used,
    )


def _needs_body() -> MailRuleEvaluation:
    return MailRuleEvaluation(
        state=MailRuleEvaluationState.NEEDS_DATA,
        required_data=MailRuleRequiredData.BODY,
    )


def _probe_result(item: OutlookMailItem) -> OutlookMailRuleProbeResult:
    return OutlookMailRuleProbeResult(
        observation=mail_rule_observation_from_item(item),
        probe=MailRuleProbeData(
            status=MailRuleProbeStatus.COMPLETE,
            body="probe-body-not-for-log",
            last_modified_date_time="2026-09-30T03:00:00Z",
            evidence_id="probe-evidence",
        ),
    )


def test_final_decision_logs_one_info_event_with_safe_correlation_fields(
    caplog,
) -> None:
    middleware, _spider = _middleware(QueueEvaluator([_matched()]))
    caplog.set_level(logging.INFO, logger=LOGGER)

    _collect(middleware, _item())

    records = [
        record
        for record in caplog.records
        if "event=outlook_mail_rule_decision" in record.getMessage()
    ]
    if len(records) != 1 or records[0].levelno != logging.INFO:
        pytest.fail("Each terminal Mail evaluation must emit one INFO decision event")
    rendered = records[0].getMessage()
    for expected in (
        "run_id='run-1'",
        "message_id='message-1'",
        "observation_kind=delta",
        "ruleset_id=ruleset-1",
        f"ruleset_digest={'a' * 64}",
        "outcome=matched",
        "profile=outlook-mail-full-v1",
        "matched_rules=r1,r2",
        "stop_rule=r2",
        "probe_used=false",
        "fallback_used=false",
    ):
        if expected not in rendered:
            pytest.fail(f"Final decision log lost field: {expected}")


def test_probe_events_are_debug_only(caplog) -> None:
    middleware, _spider = _middleware(
        QueueEvaluator([_needs_body(), _matched(probe_used=True)])
    )
    item = _item()
    caplog.set_level(logging.DEBUG, logger=LOGGER)

    _collect(middleware, item)
    _collect(middleware, _probe_result(item))

    events = {
        token: [
            record
            for record in caplog.records
            if f"event={token}" in record.getMessage()
        ]
        for token in (
            "outlook_mail_rule_probe_scheduled",
            "outlook_mail_rule_probe_completed",
        )
    }
    for token, records in events.items():
        if len(records) != 1 or records[0].levelno != logging.DEBUG:
            pytest.fail(f"{token} must be emitted exactly once at DEBUG")


def test_unresolved_logs_warning_and_final_info_and_records_fail_safe_profile(
    caplog,
) -> None:
    unresolved = MailRuleEvaluation(
        state=MailRuleEvaluationState.UNRESOLVED,
        selected_profile="outlook-mail-full-v1",
        outcome=MailRuleDecisionOutcome.UNRESOLVED,
        fallback_used=True,
        reason_code="probe_request_failed",
        ruleset_id="ruleset-1",
    )
    middleware, spider = _middleware(QueueEvaluator([unresolved]))
    caplog.set_level(logging.INFO, logger=LOGGER)

    _collect(middleware, _item())

    warnings = [
        record
        for record in caplog.records
        if "event=outlook_mail_rule_unresolved" in record.getMessage()
    ]
    decisions = [
        record
        for record in caplog.records
        if "event=outlook_mail_rule_decision" in record.getMessage()
    ]
    if len(warnings) != 1 or warnings[0].levelno != logging.WARNING:
        pytest.fail("UNRESOLVED must emit one WARNING")
    if len(decisions) != 1 or decisions[0].levelno != logging.INFO:
        pytest.fail("UNRESOLVED must still emit one final INFO decision")
    if spider.mail_rule_profiles != (("message-1", "outlook-mail-full-v1"),):
        pytest.fail("UNRESOLVED must retain its fail-safe runtime profile")


def test_evaluator_exception_preserves_item_marks_run_failed_and_logs_error_type_only(
    caplog,
) -> None:
    middleware, spider = _middleware(RaisingEvaluator())
    item = _item()
    caplog.set_level(logging.ERROR, logger=LOGGER)

    actual = _collect(middleware, item)

    if actual != [item]:
        pytest.fail("Evaluator failure must not remove the provider Mail Item")
    if (
        not spider.run_failed
        or "mail_rule_evaluation_error" not in spider.failure_reasons
    ):
        pytest.fail("Evaluator programming failure must fail logical policy integrity")
    errors = [
        record
        for record in caplog.records
        if "event=outlook_mail_rule_error" in record.getMessage()
    ]
    if len(errors) != 1:
        pytest.fail("Evaluator programming failure must emit one ERROR audit event")
    rendered = errors[0].getMessage()
    if "error_type=RuntimeError" not in rendered:
        pytest.fail("Programming error log must retain exception class only")
    if PRIVATE_EXCEPTION in rendered:
        pytest.fail("Programming error log leaked arbitrary exception text")


def test_rule_stats_are_aggregate_and_identifier_free() -> None:
    middleware, spider = _middleware(QueueEvaluator([_matched()]))

    _collect(middleware, _item())

    stats = spider.crawler.stats.get_stats()
    expected = {
        "msgloom/crawl/mail_rules/evaluated_count": 1,
        "msgloom/crawl/mail_rules/matched_count": 1,
        "msgloom/crawl/mail_rules/stop_processing_count": 1,
    }
    for key, value in expected.items():
        if stats.get(key) != value:
            pytest.fail(f"Rule aggregate stat changed: {key}={stats.get(key)!r}")
    for key in stats:
        if key.startswith("msgloom/crawl/mail_rules/") and (
            "message-1" in key or "r1" in key or "r2" in key
        ):
            pytest.fail(f"Rule identifier leaked into stat key: {key}")


def test_sensitive_mail_rule_data_is_absent_from_log_text_and_record_extras(
    caplog,
) -> None:
    middleware, _spider = _middleware(RaisingEvaluator())
    caplog.set_level(logging.DEBUG, logger=LOGGER)

    _collect(middleware, _item())

    rendered = caplog.text + "\n".join(
        repr(record.__dict__) for record in caplog.records
    )
    for secret in (
        PRIVATE_SUBJECT,
        PRIVATE_BODY,
        PRIVATE_ADDRESS,
        PRIVATE_EXCEPTION,
        "graph.example.test",
    ):
        if secret in rendered:
            pytest.fail(f"Mail rule logs leaked private source/config data: {secret}")
