"""Real Scrapy middleware/scheduler proofs for Outlook Mail acquisition policy."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest
from scrapy.core.scheduler import Scheduler
from scrapy.core.spidermw import SpiderMiddlewareManager
from scrapy.http import Request, TextResponse
from scrapy.utils.test import get_crawler

from message_ingest.acquisition.microsoft.outlook.email import (
    MailRuleEvaluation,
    MailRuleEvaluationState,
    MailRuleFact,
    MailRuleFacts,
    MailRuleObservation,
    MailRuleProbeData,
    MailRuleRequiredData,
)
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.spiders.microsoft.outlook.email.discover import (
    OutlookDiscoverSpider,
)


class NeedsBodyEvaluator:
    def evaluate(
        self,
        observation: MailRuleObservation,
        *,
        probe: MailRuleProbeData | None = None,
    ) -> MailRuleEvaluation:
        del observation, probe
        return MailRuleEvaluation(
            state=MailRuleEvaluationState.NEEDS_DATA,
            required_data=frozenset(
                {MailRuleRequiredData.BODY, MailRuleRequiredData.HEADERS}
            ),
        )


class RuleEnabledDiscoverSpider(OutlookDiscoverSpider):
    def build_mail_rule_evaluator(self, policy):
        del policy
        return NeedsBodyEvaluator()


def _item() -> OutlookMailItem:
    return OutlookMailItem.from_graph(
        {
            "id": "message-1",
            "lastModifiedDateTime": "2026-09-30T03:00:00Z",
            "bodyPreview": "preview",
        },
        source_response_url="https://graph.microsoft.com/v1.0/me/messages",
        observed_at="2026-09-30T03:00:01Z",
        observation_kind="delta",
        evidence_id="evidence-1",
        run_id="run-1",
    )


def _crawler(tmp_path: Path | None = None):
    settings = {
        "MS_GRAPH_AUTH_METHOD": "none",
        "MSGLOOM_SOURCE_IDENTITY_REQUIRED": False,
        "REFERRER_POLICY": "scrapy.spidermiddlewares.referer.DefaultReferrerPolicy",
    }
    if tmp_path is not None:
        settings.update(
            {
                "JOBDIR": str(tmp_path / "job"),
                "SCHEDULER_DEBUG": True,
                "SCHEDULER_PRIORITY_QUEUE": "scrapy.pqueues.ScrapyPriorityQueue",
            }
        )
    crawler = get_crawler(RuleEnabledDiscoverSpider, settings_dict=settings)
    spider = RuleEnabledDiscoverSpider.from_crawler(crawler)
    crawler.spider = spider
    return crawler, spider


def test_real_spider_middleware_chain_processes_generated_probe_request(
    tmp_path: Path,
) -> None:
    crawler, _spider = _crawler(tmp_path)
    manager = SpiderMiddlewareManager.from_crawler(crawler)
    source_request = Request(
        "https://graph.microsoft.com/v1.0/me/messages?$top=1",
        meta={"depth": 2},
    )
    response = TextResponse(
        source_request.url,
        request=source_request,
        body=b"{}",
        encoding="utf-8",
    )
    item = _item()

    async def scrape_func(_response, _request):
        return [item]

    async def collect():
        chain = await manager.scrape_response_async(
            scrape_func,
            response,
            source_request,
        )
        return [output async for output in chain]

    outputs = asyncio.run(collect())
    if outputs[0] is not item or len(outputs) != 2:
        pytest.fail(
            "Real Spider Middleware chain must preserve Item then add one probe"
        )
    probe = outputs[1]
    if not isinstance(probe, Request):
        pytest.fail("Mail rule middleware must add a Scrapy Request")
    if probe.meta.get("depth") != 3:
        pytest.fail("Generated probe must continue through native DepthMiddleware")
    if probe.headers.get(b"Referer") != source_request.url.encode():
        pytest.fail("Generated probe must continue through native RefererMiddleware")
    if probe.cb_kwargs.get("required_data") != frozenset(
        {MailRuleRequiredData.BODY, MailRuleRequiredData.HEADERS}
    ):
        pytest.fail("Real middleware chain lost composite required-data context")


def test_probe_request_round_trips_through_disk_scheduler_jobdir(
    tmp_path: Path,
) -> None:
    crawler1, spider1 = _crawler(tmp_path)
    scheduler1 = Scheduler.from_crawler(crawler1)
    scheduler1.open(spider1)
    observation = MailRuleObservation(
        message_id="message-1",
        run_id="run-1",
        evidence_id="evidence-1",
        observation_kind="delta",
        facts=MailRuleFacts(
            change_key="change-1",
            last_modified_date_time="2026-09-30T03:00:00Z",
            available_facts=frozenset(
                {
                    MailRuleFact.CHANGE_KEY,
                    MailRuleFact.LAST_MODIFIED_DATE_TIME,
                }
            ),
        ),
    )
    required_data = frozenset({MailRuleRequiredData.BODY, MailRuleRequiredData.HEADERS})
    request = spider1.mail_rule_probe_request(observation, required_data)

    if scheduler1.enqueue_request(request) is not True:
        pytest.fail("Probe request was not accepted by the native Scheduler")
    stats1 = crawler1.stats.get_stats()
    if stats1.get("scheduler/enqueued/disk") != 1:
        pytest.fail("Serializable rule probe must use the JOBDIR disk queue")
    if stats1.get("scheduler/unserializable", 0):
        pytest.fail("Serializable rule probe unexpectedly fell back to memory")
    scheduler1.close("test-pause")

    crawler2, spider2 = _crawler(tmp_path)
    scheduler2 = Scheduler.from_crawler(crawler2)
    scheduler2.open(spider2)
    restored = scheduler2.next_request()
    if restored is None:
        pytest.fail("Queued rule probe did not survive JOBDIR reconstruction")
    if restored.callback != spider2.parse_mail_rule_probe:
        pytest.fail("Restored JOBDIR callback is not bound to the fresh Spider")
    if restored.errback != spider2.mail_rule_probe_errback:
        pytest.fail("Restored JOBDIR errback is not bound to the fresh Spider")
    if restored.cb_kwargs.get("observation") != observation:
        pytest.fail("Restored JOBDIR rule observation context changed")
    if restored.cb_kwargs.get("required_data") != required_data:
        pytest.fail("Restored JOBDIR composite required-data context changed")
    if crawler2.stats.get_value("scheduler/dequeued/disk") != 1:
        pytest.fail("Restored rule probe must be read from the JOBDIR disk queue")
    if crawler2.stats.get_value("scheduler/unserializable", 0):
        pytest.fail("JOBDIR restore reported an unserializable rule probe")
    scheduler2.close("finished")


def test_no_rules_disables_mail_rule_middleware_without_warning(
    caplog,
) -> None:
    crawler = get_crawler(OutlookDiscoverSpider)
    spider = OutlookDiscoverSpider.from_crawler(crawler)
    crawler.spider = spider
    caplog.set_level(logging.WARNING, logger="scrapy.middleware")

    manager = SpiderMiddlewareManager.from_crawler(crawler)

    if any(
        type(middleware).__name__ == "OutlookMailAcquisitionRuleMiddleware"
        for middleware in manager.middlewares
    ):
        pytest.fail("No-rules crawl must not enable Mail acquisition-rule middleware")
    if "OutlookMailAcquisitionRuleMiddleware" in caplog.text:
        pytest.fail("Normal no-rules crawl must disable Mail rule middleware silently")
