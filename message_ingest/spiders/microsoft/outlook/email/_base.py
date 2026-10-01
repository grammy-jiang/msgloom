"""Outlook Mail resource contracts layered on Microsoft Graph transport."""

from __future__ import annotations

from abc import ABC
from collections.abc import Iterator
from typing import Any, ClassVar

import scrapy
from scrapy.http import TextResponse
from scrapy.settings import BaseSettings
from twisted.python.failure import Failure

from message_ingest.acquisition.microsoft.outlook.email import (
    MailRuleEvaluator,
    MailRuleFact,
    MailRuleFacts,
    MailRuleObservation,
    MailRuleProbeData,
    MailRuleProbeFailure,
    MailRuleProbeStatus,
    OutlookMailRuleProbeResult,
)
from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.spiders.microsoft.outlook._mailbox import OutlookMailboxSpider
from microsoft_graph.protocol import graph_object
from microsoft_graph.spiders.outlook.mail import OutlookMailSpider as GraphMail


class OutlookMailSpider(GraphMail, OutlookMailboxSpider, ABC):
    """
    Add Mail provenance and failure context to provider acquisition.

    The framework Mail base owns scopes, fields, and immutable-ID preference.
    This adapter adds provenance and failure callback context, using
    the msgloom Graph base for evidence and logical run integrity.
    """

    failure_context_keys: ClassVar[tuple[str, ...]] = (
        "message_id",
        "attachment_id",
        "folder_id",
    )

    def _message_item(
        self,
        message: dict[str, Any],
        source_response_url: str,
        observed_at: str,
        *,
        observation_kind: str,
        evidence_id: str | None,
    ) -> OutlookMailItem:
        """Retain the raw message beside searchable Mail projections."""
        return OutlookMailItem.from_graph(
            message,
            source_response_url=source_response_url,
            observed_at=observed_at,
            observation_kind=observation_kind,
            evidence_id=evidence_id,
            run_id=self.run_id,
        )


class OutlookMailCollectionSpider(OutlookMailSpider, ABC):
    """
    Mark spiders that emit message observations for acquisition policy.

    Discovery and delta collection share this boundary. Folder lifecycle and
    Full-profile execution deliberately remain outside it so Mail rule
    middleware can be enabled only where an initial message decision exists.
    """

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Register the Mail-only Spider Middleware without a global setting."""
        super().update_settings(settings)
        from message_ingest.spidermiddlewares.microsoft.outlook.email import (
            OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY,
            OutlookMailAcquisitionRuleMiddleware,
        )

        settings.setdefault_in_component_priority_dict(
            "SPIDER_MIDDLEWARES",
            OutlookMailAcquisitionRuleMiddleware,
            OUTLOOK_MAIL_RULE_MIDDLEWARE_PRIORITY,
        )

    @classmethod
    def build_mail_rule_evaluator(cls, crawler) -> MailRuleEvaluator | None:
        """Return the configured pure evaluator; later rule work overrides this."""
        del crawler
        return None

    def __init__(self, *args, **kwargs) -> None:
        """Initialize attempt-local rule state without durable side effects."""
        super().__init__(*args, **kwargs)
        self._mail_rule_evaluator: MailRuleEvaluator | None = None
        self._mail_rule_profiles: dict[str, str] = {}

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Bind one evaluator instance after Scrapy has created the crawler."""
        spider = super().from_crawler(crawler, *args, **kwargs)
        spider._mail_rule_evaluator = cls.build_mail_rule_evaluator(crawler)
        return spider

    @property
    def mail_rule_evaluator(self) -> MailRuleEvaluator | None:
        """Expose the attempt-local evaluator to the Mail Spider Middleware."""
        return self._mail_rule_evaluator

    def mail_rule_probe_request(
        self,
        observation: MailRuleObservation,
    ) -> scrapy.Request:
        """Build one bounded, JOBDIR-serializable body probe request."""
        return self.graph_request(
            self.message_path(
                observation.message_id,
                fields=("id", "changeKey", "body", "bodyPreview"),
            ),
            callback=self.parse_mail_rule_probe,
            errback=self.mail_rule_probe_errback,
            operation="mail-rule-probe",
            cb_kwargs={
                "purpose": "mail-rule-probe",
                "observation": observation,
            },
            prefer=self.compose_prefer('outlook.body-content-type="text"'),
            dont_cache=True,
        )

    def parse_mail_rule_probe(
        self,
        response: TextResponse,
        *,
        purpose: str,
        observation: MailRuleObservation,
    ) -> Iterator[Any]:
        """Preserve source evidence and emit one bounded internal probe result."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence

        try:
            payload = graph_object(response.json(), context="Outlook Mail rule probe")
            body = payload.get("body")
            change_key = payload.get("changeKey")
            preview = payload.get("bodyPreview")
            content = body.get("content") if isinstance(body, dict) else None
            content_type = body.get("contentType") if isinstance(body, dict) else None
            valid = (
                payload.get("id") == observation.message_id
                and isinstance(change_key, str)
                and isinstance(content, str)
                and content_type == "text"
            )
        except (TypeError, ValueError):
            valid = False
            change_key = None
            preview = None
            content = None

        if valid:
            available = {MailRuleFact.CHANGE_KEY, MailRuleFact.BODY}
            body_preview = (
                preview if isinstance(preview, str) and len(preview) <= 1024 else None
            )
            if body_preview is not None:
                available.add(MailRuleFact.BODY_PREVIEW)
            probe = MailRuleProbeData(
                status=MailRuleProbeStatus.COMPLETE,
                facts=MailRuleFacts(
                    change_key=change_key,
                    body=content,
                    body_preview=body_preview,
                    available_facts=frozenset(available),
                ),
                evidence_id=evidence.evidence_id,
            )
        else:
            probe = MailRuleProbeData(
                status=MailRuleProbeStatus.FAILED,
                facts=MailRuleFacts(),
                evidence_id=evidence.evidence_id,
                failures=(
                    MailRuleProbeFailure(
                        fact=MailRuleFact.BODY,
                        reason_code="invalid_probe_payload",
                    ),
                ),
            )
        yield OutlookMailRuleProbeResult(observation=observation, probe=probe)

    def mail_rule_probe_errback(self, failure: Failure) -> Iterator[Any]:
        """Convert exhausted probe acquisition into bounded unresolved input."""
        request = self._failure_request(failure)
        observation = request.cb_kwargs.get("observation")
        if not isinstance(observation, MailRuleObservation):
            raise TypeError("Mail rule probe failure lost observation context")

        evidence = self._failure_evidence_item(failure)
        yield evidence
        yield OutlookMailRuleProbeResult(
            observation=observation,
            probe=MailRuleProbeData(
                status=MailRuleProbeStatus.FAILED,
                facts=MailRuleFacts(),
                evidence_id=evidence.evidence_id,
                failures=(
                    MailRuleProbeFailure(
                        fact=MailRuleFact.BODY,
                        reason_code="probe_request_failed",
                    ),
                ),
            ),
        )

    def record_mail_rule_profile(self, *, message_id: str, profile: str) -> None:
        """Retain only the latest attempt-local acquisition profile per message."""
        self._mail_rule_profiles[message_id] = profile

    @property
    def mail_rule_profiles(self) -> tuple[tuple[str, str], ...]:
        """Return an immutable insertion-ordered snapshot of runtime selections."""
        return tuple(self._mail_rule_profiles.items())
