"""Publish proven non-authoritative subjects at the native-idle boundary.

Full profiles and supported discovery use evidence-backed completion proof.
Authority stores retain all promotion rights. Other traversal paths are gated.
"""

from __future__ import annotations

from datetime import UTC, datetime

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from message_ingest.acquisition.handoff import (
    AcquisitionStream,
    ReleaseEntrySpec,
    ReleaseGroupSpec,
    ReleaseKind,
)
from message_ingest.acquisition.microsoft.outlook.calendar.full_completion import (
    verify_full_v1_target as verify_calendar,
)
from message_ingest.acquisition.microsoft.outlook.email.full_completion import (
    verify_full_v1_target as verify_mail,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.extensions._handoff_onedrive import release_onedrive_content
from message_ingest.extensions._handoff_traversal import (
    TRAVERSALS,
    release_traversal,
)
from message_ingest.extensions.catalog import CatalogService


class HandoffReleaseExtension:
    """Release proven profiles and traversals before pipeline shutdown."""

    def __init__(self, crawler):
        """Keep failures local to their target when the signal identifies it."""
        self.crawler = crawler
        self.failed_targets: set[str] = set()
        self.unknown_failure = False
        self.handled = False

    @classmethod
    def from_crawler(cls, crawler):
        """Enable the same native lifecycle for public and direct crawls."""
        if crawler.spidercls.name not in {
            "microsoft_onedrive_content",
            "outlook_full",
            "outlook_calendar_full",
            *TRAVERSALS,
        }:
            raise NotConfigured(
                "Handoff release requires a supported completion verifier"
            )
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Handoff release requires the catalog")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_idle, signal=signals.spider_idle)
        crawler.signals.connect(extension.spider_error, signal=signals.spider_error)
        crawler.signals.connect(extension.item_error, signal=signals.item_error)
        crawler.signals.connect(extension.item_error, signal=signals.item_dropped)
        return extension

    def _record_failure(self, target):
        if isinstance(target, str) and target:
            self.failed_targets.add(target)
        else:
            self.unknown_failure = True

    def spider_error(self, response=None, **kwargs):
        """Block callback failures without depending on signal-handler order."""
        request = getattr(response, "request", None)
        context = getattr(request, "cb_kwargs", {})
        target = context.get("message_id") or context.get("event_id")
        if self.crawler.spidercls.name == "microsoft_onedrive_content":
            target = context.get("item_id")
        self._record_failure(target)

    def item_error(self, item, **kwargs):
        """Block failed or dropped target items; unknown ownership fails closed."""
        target = getattr(item, "message_id", None) or getattr(item, "event_id", None)
        if self.crawler.spidercls.name == "microsoft_onedrive_content":
            target = getattr(item, "item_id", None)
        self._record_failure(target)

    def spider_idle(self, spider):
        """
        Verify and publish synchronously in each target's writer transaction.

        Scrapy 2.19 native idle excludes pending requests and item processing.
        No background write, close reason, or signal ordering proves success.
        Request failures can be terminal profile limitations; the target
        verifier decides whether their persisted facts are complete.
        """
        if self.handled or self.unknown_failure:
            return
        if not self.crawler.settings.getbool("MSGLOOM_RAW_EVIDENCE_ENABLED"):
            return
        traversal = spider.name in TRAVERSALS
        if traversal and (spider.run_failed or self.failed_targets):
            return
        reasons = spider.failure_reasons
        allowed = {"spider_error", "item_error", "item_dropped"}
        if any(
            not reason.startswith("request_failure:") and reason not in allowed
            for reason in reasons
        ):
            return
        # A resumed failure has no in-memory target attribution. Fail closed.
        if reasons & allowed and not self.failed_targets:
            return
        service = CatalogService.from_crawler(self.crawler)
        if service.write_lock.locked():
            spider.mark_run_failed("handoff_write_busy")
            return
        source = self.crawler.settings.get("MSGLOOM_SOURCE_ID")
        if not isinstance(source, str) or not source:
            spider.mark_run_failed("handoff_source_missing")
            return
        if traversal:
            self.handled = True
            try:
                with service.catalog.writer_session() as writer:
                    release_traversal(service.catalog, writer, source, spider)
            except Exception as error:
                spider.mark_run_failed("handoff_release_failed")
                raise CloseSpider("handoff_release_failed") from error
            return
        if spider.name == "microsoft_onedrive_content":
            self.handled = True
            try:
                for target in spider.item_ids:
                    if target in self.failed_targets:
                        continue
                    with service.catalog.writer_session() as writer:
                        release_onedrive_content(
                            service.catalog, writer, source, spider, target
                        )
            except Exception as error:
                spider.mark_run_failed("handoff_release_failed")
                raise CloseSpider("handoff_release_failed") from error
            return
        mail = spider.name == "outlook_full"
        targets = spider.message_ids if mail else spider.event_ids
        verifier = verify_mail if mail else verify_calendar
        # Enrich can reuse exact stored profile facts, including no-work
        # targets. Refresh and authority obligations still need this attempt.
        require_current_attempt = spider.operation != "enrich" or getattr(
            spider, "_authoritative_rule_refresh", False
        )
        stream = (
            AcquisitionStream.OUTLOOK_MAIL
            if mail
            else AcquisitionStream.OUTLOOK_CALENDAR
        )
        self.handled = True
        try:
            for target in targets:
                if target in self.failed_targets:
                    continue
                with service.catalog.writer_session() as writer:
                    proof = verifier(
                        service.catalog,
                        source_id=source,
                        run_id=spider.run_id,
                        require_current_attempt=require_current_attempt,
                        writer=writer,
                        **({"message_id": target} if mail else {"event_id": target}),
                    )
                    if not proof.complete:
                        continue
                    identity = (proof.resource_kind, proof.resource_identity)
                    members = []
                    for fact in proof.required_facts:
                        own = (fact.resource_kind, fact.resource_identity)
                        parent = (
                            fact.parent_resource_kind,
                            fact.parent_resource_identity,
                        )
                        role = (
                            "primary"
                            if own == identity and fact.component_kind is None
                            else "component"
                            if identity in (own, parent)
                            else "proof"
                        )
                        members.append((fact.fact_id, role))
                    group = ReleaseGroupSpec(
                        source_id=source,
                        stream=stream,
                        release_kind=ReleaseKind.RESOURCE_PROFILE,
                        subject_kind=proof.resource_kind,
                        subject_identity=target,
                        owner_run_id=spider.run_id,
                        released_at=datetime.now(UTC).isoformat(),
                        coverage_kind=(
                            "terminal_with_limitations"
                            if proof.terminal_with_limitations
                            else "complete"
                        ),
                        profile=spider.profile,
                        limitation_codes=proof.limitation_codes,
                    )
                    entry = ReleaseEntrySpec(
                        resource_kind=proof.resource_kind,
                        resource_identity=target,
                        facts=tuple(members),
                    )
                    AcquisitionHandoffStore(
                        service.catalog
                    ).release_effective_group_in_session(writer, group, [entry])
        except Exception as error:
            spider.mark_run_failed("handoff_release_failed")
            raise CloseSpider("handoff_release_failed") from error
