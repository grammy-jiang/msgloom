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
