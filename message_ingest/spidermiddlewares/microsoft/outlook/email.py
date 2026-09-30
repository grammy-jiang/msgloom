"""Outlook Mail acquisition-policy adapter at the Spider output boundary."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from scrapy.exceptions import NotConfigured
from scrapy.http import Response

from message_ingest.acquisition.microsoft.outlook.email import (
    MailRuleEvaluationState,
    MailRuleEvaluator,
    mail_rule_observation_from_item,
)
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.spiders.microsoft.outlook.email._base import (
    OutlookMailCollectionSpider,
)

OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY = 1100


class OutlookMailAcquisitionRuleMiddleware:
    """Stream Mail collection output through a future deterministic evaluator."""

    def __init__(
        self,
        crawler,
        spider: OutlookMailCollectionSpider,
        evaluator: MailRuleEvaluator,
    ) -> None:
        self.crawler = crawler
        self.spider = spider
        self.evaluator = evaluator

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only for Mail collection spiders with an evaluator."""

        spider = crawler.spider
        if not isinstance(spider, OutlookMailCollectionSpider):
            raise NotConfigured(
                "Outlook Mail rule middleware requires collection spider"
            )
        evaluator = spider.mail_rule_evaluator
        if evaluator is None:
            raise NotConfigured("Outlook Mail rule evaluator is not configured")
        return cls(crawler, spider, evaluator)

    async def process_spider_output(
        self,
        response: Response,
        result: AsyncIterator[Any],
    ) -> AsyncIterator[Any]:
        """Preserve streaming output until policy handling is implemented."""

        del response
        async for output in result:
            yield output
            if not isinstance(output, OutlookMailItem):
                continue
            observation = mail_rule_observation_from_item(output)
            evaluation = self.evaluator.evaluate(observation, probe=None)
            if evaluation.state is not MailRuleEvaluationState.FINAL:
                continue
            profile = evaluation.selected_profile
            if profile is None:
                raise RuntimeError("validated final Mail rule evaluation lost profile")
            self.spider.record_mail_rule_profile(
                message_id=observation.message_id,
                profile=profile,
            )


__all__ = [
    "OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY",
    "OutlookMailAcquisitionRuleMiddleware",
]
