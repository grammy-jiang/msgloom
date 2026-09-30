"""Outlook Mail acquisition-policy adapter at the Spider output boundary."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from scrapy.exceptions import NotConfigured
from scrapy.http import Response

from message_ingest.acquisition.microsoft.outlook.email import (
    MailRuleEvaluation,
    MailRuleEvaluationState,
    MailRuleEvaluator,
    MailRuleObservation,
    MailRuleRequiredData,
    OutlookMailRuleProbeResult,
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
        self._scheduled_body_probes: set[tuple[str, str | None, str, str | None]] = (
            set()
        )

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
            if isinstance(output, OutlookMailRuleProbeResult):
                evaluation = self.evaluator.evaluate(
                    output.observation,
                    probe=output.probe,
                )
                if evaluation.state is MailRuleEvaluationState.NEEDS_DATA:
                    self.spider.mark_run_failed("mail_rule_probe_loop")
                    continue
                self._record_terminal(output.observation, evaluation)
                continue

            yield output
            if not isinstance(output, OutlookMailItem):
                continue

            observation = mail_rule_observation_from_item(output)
            evaluation = self.evaluator.evaluate(observation, probe=None)
            if evaluation.state is MailRuleEvaluationState.NEEDS_DATA:
                if evaluation.required_data is not MailRuleRequiredData.BODY:
                    raise RuntimeError("unsupported Mail rule required-data state")
                key = self._probe_key(observation)
                if key in self._scheduled_body_probes:
                    continue
                self._scheduled_body_probes.add(key)
                yield self.spider.mail_rule_probe_request(observation)
                continue
            self._record_terminal(observation, evaluation)

    @staticmethod
    def _probe_key(
        observation: MailRuleObservation,
    ) -> tuple[str, str | None, str, str | None]:
        return (
            observation.message_id,
            observation.evidence_id,
            observation.observation_kind,
            observation.run_id,
        )

    def _record_terminal(
        self,
        observation: MailRuleObservation,
        evaluation: MailRuleEvaluation,
    ) -> None:
        if evaluation.state not in {
            MailRuleEvaluationState.FINAL,
            MailRuleEvaluationState.UNRESOLVED,
        }:
            raise RuntimeError("Mail rule evaluation did not reach terminal state")
        profile = evaluation.selected_profile
        if profile is None:
            raise RuntimeError("validated terminal Mail rule evaluation lost profile")
        self.spider.record_mail_rule_profile(
            message_id=observation.message_id,
            profile=profile,
        )


__all__ = [
    "OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY",
    "OutlookMailAcquisitionRuleMiddleware",
]
