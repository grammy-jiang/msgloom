"""Outlook Mail acquisition-policy adapter at the Spider output boundary."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from scrapy.exceptions import NotConfigured
from scrapy.http import Response

from message_ingest.acquisition.microsoft.outlook.email import (
    MailRuleDecisionOutcome,
    MailRuleEvaluation,
    MailRuleEvaluationState,
    MailRuleEvaluator,
    MailRuleObservation,
    MailRuleProbeStatus,
    OutlookMailRuleProbeResult,
    mail_rule_observation_from_item,
)
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.spiders.microsoft.outlook.email._base import (
    OutlookMailCollectionSpider,
)

logger = logging.getLogger(__name__)

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
        self._scheduled_probes: set[tuple[str, str | None, str, str | None]] = set()

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
            raise NotConfigured
        return cls(crawler, spider, evaluator)

    async def process_spider_output(
        self,
        response: Response,
        result: AsyncIterator[Any],
    ) -> AsyncIterator[Any]:
        """Preserve source output while applying bounded acquisition policy."""

        del response
        async for output in result:
            if isinstance(output, OutlookMailRuleProbeResult):
                self._publish_probe_result(output)
                try:
                    evaluation = self._evaluate(
                        output.observation,
                        probe=output.probe,
                    )
                    if evaluation.state is MailRuleEvaluationState.NEEDS_DATA:
                        self._programming_failure(
                            message_id=output.observation.message_id,
                            run_id=output.observation.run_id,
                            phase="probe",
                            reason="mail_rule_probe_loop",
                            error_type="InvalidRuleState",
                        )
                        continue
                    self._record_terminal(output.observation, evaluation)
                except Exception as exc:  # noqa: BLE001 - policy boundary must fail closed
                    self._programming_failure(
                        message_id=output.observation.message_id,
                        run_id=output.observation.run_id,
                        phase="probe",
                        reason="mail_rule_evaluation_error",
                        error_type=type(exc).__name__,
                    )
                continue

            yield output
            if not isinstance(output, OutlookMailItem):
                continue

            try:
                observation = mail_rule_observation_from_item(output)
                evaluation = self._evaluate(observation, probe=None)
                if evaluation.state is MailRuleEvaluationState.NEEDS_DATA:
                    key = self._probe_key(observation)
                    if key in self._scheduled_probes:
                        continue
                    request = self.spider.mail_rule_probe_request(
                        observation,
                        evaluation.required_data,
                    )
                    self._scheduled_probes.add(key)
                    self.crawler.stats.inc_value(
                        "msgloom/crawl/mail_rules/probe_scheduled_count"
                    )
                    required_data = ",".join(
                        sorted(value.value for value in evaluation.required_data)
                    )
                    logger.debug(
                        "Outlook Mail rule probe: "
                        "event=outlook_mail_rule_probe_scheduled "
                        "run_id=%r message_id=%r required_data=%s",
                        observation.run_id,
                        observation.message_id,
                        required_data,
                        extra={"spider": self.spider},
                    )
                    yield request
                    continue
                self._record_terminal(observation, evaluation)
            except Exception as exc:  # noqa: BLE001 - policy boundary preserves source Item
                self._programming_failure(
                    message_id=output.message_id,
                    run_id=output.run_id,
                    phase="initial",
                    reason="mail_rule_evaluation_error",
                    error_type=type(exc).__name__,
                )

    def _evaluate(
        self,
        observation: MailRuleObservation,
        *,
        probe=None,
    ) -> MailRuleEvaluation:
        evaluation = self.evaluator.evaluate(observation, probe=probe)
        if not isinstance(evaluation, MailRuleEvaluation):
            raise TypeError("Mail rule evaluator returned invalid result type")
        return evaluation

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

    def _publish_probe_result(self, result: OutlookMailRuleProbeResult) -> None:
        status = result.probe.status
        if status is MailRuleProbeStatus.COMPLETE:
            self.crawler.stats.inc_value(
                "msgloom/crawl/mail_rules/probe_completed_count"
            )
        elif status is MailRuleProbeStatus.PARTIAL:
            self.crawler.stats.inc_value("msgloom/crawl/mail_rules/probe_partial_count")
        else:
            self.crawler.stats.inc_value("msgloom/crawl/mail_rules/probe_failed_count")
        logger.debug(
            "Outlook Mail rule probe: "
            "event=outlook_mail_rule_probe_completed "
            "run_id=%r message_id=%r status=%s reason=%s",
            result.observation.run_id,
            result.observation.message_id,
            status.value,
            result.probe.reason_code or "-",
            extra={"spider": self.spider},
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
        outcome = evaluation.outcome
        if profile is None or outcome is None:
            raise RuntimeError("validated terminal Mail rule evaluation lost fields")

        self.crawler.stats.inc_value("msgloom/crawl/mail_rules/evaluated_count")
        if outcome is MailRuleDecisionOutcome.MATCHED:
            self.crawler.stats.inc_value("msgloom/crawl/mail_rules/matched_count")
        elif outcome is MailRuleDecisionOutcome.DEFAULT:
            self.crawler.stats.inc_value("msgloom/crawl/mail_rules/default_count")
        elif outcome is MailRuleDecisionOutcome.UNRESOLVED:
            self.crawler.stats.inc_value("msgloom/crawl/mail_rules/unresolved_count")
        else:
            raise RuntimeError("unknown terminal Mail rule outcome")

        if evaluation.stop_rule_id is not None:
            self.crawler.stats.inc_value(
                "msgloom/crawl/mail_rules/stop_processing_count"
            )
        if evaluation.fallback_used:
            self.crawler.stats.inc_value("msgloom/crawl/mail_rules/fallback_count")

        self.spider.record_mail_rule_profile(
            message_id=observation.message_id,
            profile=profile,
        )

        if evaluation.state is MailRuleEvaluationState.UNRESOLVED:
            logger.warning(
                "Outlook Mail rule unresolved: "
                "event=outlook_mail_rule_unresolved "
                "run_id=%r message_id=%r reason=%s profile=%s",
                observation.run_id,
                observation.message_id,
                evaluation.reason_code or "unknown",
                profile,
                extra={"spider": self.spider},
            )

        logger.info(
            "Outlook Mail rule decision: "
            "event=outlook_mail_rule_decision "
            "run_id=%r message_id=%r observation_kind=%s "
            "ruleset_id=%s outcome=%s profile=%s "
            "matched_rules=%s stop_rule=%s probe_used=%s fallback_used=%s",
            observation.run_id,
            observation.message_id,
            observation.observation_kind,
            evaluation.ruleset_id or "-",
            outcome.value,
            profile,
            ",".join(evaluation.matched_rule_ids) or "-",
            evaluation.stop_rule_id or "-",
            str(evaluation.probe_used).lower(),
            str(evaluation.fallback_used).lower(),
            extra={"spider": self.spider},
        )

    def _programming_failure(
        self,
        *,
        message_id: str,
        run_id: str | None,
        phase: str,
        reason: str,
        error_type: str,
    ) -> None:
        self.spider.mark_run_failed(reason)
        self.crawler.stats.inc_value("msgloom/crawl/mail_rules/evaluation_error_count")
        logger.error(
            "Outlook Mail rule error: event=outlook_mail_rule_error "
            "run_id=%r message_id=%r phase=%s reason=%s error_type=%s",
            run_id,
            message_id,
            phase,
            reason,
            error_type,
            extra={"spider": self.spider},
        )


__all__ = [
    "OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY",
    "OutlookMailAcquisitionRuleMiddleware",
]
