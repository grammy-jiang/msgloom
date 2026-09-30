"""Publish terminal Outlook crawl status through Scrapy stats and logs."""

from __future__ import annotations

import logging
import re
from typing import ClassVar
from uuid import uuid4

from scrapy import signals
from scrapy.exceptions import NotConfigured

from message_ingest.spiders.microsoft.outlook.email._base import OutlookMailSpider

logger = logging.getLogger(__name__)


class OutlookCrawlStatusExtension:
    """
    Report one crawl attempt without owning business correctness.

    Delta checkpoint safety remains in the delta checkpoint extension. This
    extension observes Scrapy lifecycle and error signals, classifies terminal
    execution state, and writes a bounded summary after pipeline shutdown. It
    never queries the catalog or decides whether provider state may be
    committed.
    """

    _mode_by_spider: ClassVar[dict[str, str]] = {
        "outlook_discover": "discovery",
        "outlook_delta": "delta",
        "outlook_full": "full",
    }
    _safe_reason = re.compile(r"[A-Za-z0-9_.:-]{1,96}")

    def __init__(self, crawler) -> None:
        """Keep attempt-local lifecycle observations beside crawler stats."""
        self.crawler = crawler
        self.attempt_id = uuid4().hex
        self._spider_error = False
        self._item_error = False
        self._item_dropped = False

    @classmethod
    def from_crawler(cls, crawler):
        """Register lifecycle observation when status reporting is enabled."""
        if not crawler.settings.getbool("MSGLOOM_CRAWL_STATUS_ENABLED"):
            raise NotConfigured("msgloom crawl status extension disabled")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(extension.spider_error, signal=signals.spider_error)
        crawler.signals.connect(extension.item_error, signal=signals.item_error)
        crawler.signals.connect(extension.item_dropped, signal=signals.item_dropped)
        crawler.signals.connect(extension.spider_closed, signal=signals.spider_closed)
        return extension

    @staticmethod
    def _is_outlook_spider(spider) -> bool:
        """Limit this extension to the shared Outlook spider hierarchy."""
        return isinstance(spider, OutlookMailSpider)

    def spider_opened(self, spider) -> None:
        """Publish attempt identity before requests start."""
        if not self._is_outlook_spider(spider):
            return
        mode = self._mode_by_spider.get(spider.name, "unknown")
        stats = self.crawler.stats
        stats.set_value("msgloom/final/status", "running")
        stats.set_value("msgloom/final/schema_version", 1)
        stats.set_value("msgloom/final/spider", spider.name)
        stats.set_value("msgloom/final/mode", mode)
        stats.set_value("msgloom/final/attempt_id", self.attempt_id)
        stats.set_value(
            "msgloom/final/jobdir_enabled",
            bool(self.crawler.settings.get("JOBDIR")),
        )
        stats.set_value("msgloom/final/counter_scope", "attempt")

    def spider_error(self, spider, **_kwargs) -> None:
        """Remember callback/start failures independently of checkpoint settings."""
        if self._is_outlook_spider(spider):
            self._spider_error = True

    def item_error(self, spider, **_kwargs) -> None:
        """Own the one project counter for non-DropItem pipeline failures."""
        if not self._is_outlook_spider(spider):
            return
        self._item_error = True
        self.crawler.stats.inc_value("msgloom/persistence/item_error_count")

    def item_dropped(self, spider, **_kwargs) -> None:
        """Remember dropped acquisition items; Scrapy owns the native counter."""
        if self._is_outlook_spider(spider):
            self._item_dropped = True

    def spider_closed(self, spider, reason: str) -> None:
        """
        Classify the attempt after Scrapy closes item pipelines.

        Scrapy 2.19 emits spider_closed before StatsCollector.close_spider.
        Signal handler order is undefined, so this method uses its reason
        argument directly and never depends on native finish_reason being
        present.
        """
        if not self._is_outlook_spider(spider):
            return

        stats = self.crawler.stats
        mode = stats.get_value(
            "msgloom/crawl/mode",
            self._mode_by_spider.get(spider.name, "unknown"),
        )
        status = self._terminal_status(spider, mode, reason)
        reason_codes = self._reason_codes(spider, reason, status)
        counter_scope = "attempt"
        if mode == "delta" and stats.get_value(
            "msgloom/crawl/delta/job_resumed", False
        ):
            counter_scope = "attempt_with_restored_run_state"

        stats.set_value("msgloom/final/status", status)
        stats.set_value("msgloom/final/close_reason", reason)
        stats.set_value("msgloom/final/run_id", spider.run_id)
        stats.set_value("msgloom/final/reason_codes", reason_codes)
        stats.set_value("msgloom/final/counter_scope", counter_scope)
        stats.set_value(
            "msgloom/final/framework_close_error_count",
            int(stats.get_value("msgloom/lifecycle/close_error_count", 0) or 0),
        )

        if mode == "discovery":
            self._publish_discovery(spider, status, reason)
            self._publish_mail_rule_summary(spider)
        elif mode == "delta":
            self._publish_delta(spider, status, reason)
            self._publish_mail_rule_summary(spider)
        elif mode == "full":
            self._publish_full(spider, status, reason)
        else:
            logger.info(
                "Outlook crawl final summary: status=%s reason=%s "
                "spider=%s run_id=%s attempt_id=%s",
                status,
                reason,
                spider.name,
                spider.run_id,
                self.attempt_id,
                extra={"spider": spider},
            )

    def _known_failure(self, spider, reason: str) -> bool:
        """Return whether an observed signal or integrity fact failed."""
        stats = self.crawler.stats
        return bool(
            self._spider_error
            or self._item_error
            or self._item_dropped
            or spider.run_failed
            or stats.get_value("spider_exceptions/count", 0)
            or stats.get_value("msgloom/lifecycle/close_error_count", 0)
            or stats.get_value("msgloom/lifecycle/signal_error_count", 0)
            or reason
            in {
                "start_error",
                "checkpoint_candidate_load_failed",
                "checkpoint_evaluation_failed",
                "checkpoint_commit_failed",
                "closespider_errorcount",
            }
        )

    def _terminal_status(self, spider, mode: str, reason: str) -> str:
        """Map concrete execution facts to a small status vocabulary."""
        if self._known_failure(spider, reason):
            return "failed"
        if mode == "delta" and reason == "delta_incomplete":
            return "incomplete"
        if reason != "finished":
            return "interrupted"

        stats = self.crawler.stats
        if mode == "discovery":
            if stats.get_value("msgloom/crawl/discovery/truncated_count", 0):
                return "truncated"
            if stats.get_value("msgloom/crawl/discovery/pagination_exhausted", False):
                return "completed"
            return "unverified"

        if mode == "delta":
            outcome = self._checkpoint_outcome()
            if outcome == "committed":
                return "completed"
            if outcome == "skipped":
                return "incomplete"
            if outcome == "error":
                return "failed"
            return "unverified"

        if mode == "full":
            return "completed"
        return "unverified"

    def _checkpoint_outcome(self) -> str:
        """Describe checkpoint observation without inferring it from counters."""
        if not self.crawler.settings.getbool("MSGLOOM_DELTA_CHECKPOINT_ENABLED"):
            return "disabled"
        value = self.crawler.stats.get_value("msgloom/checkpoint/outcome")
        if value in {"committed", "skipped", "error"}:
            return value
        if value == "evaluating":
            return "error"
        return "unknown"

    def _reason_codes(self, spider, reason: str, status: str) -> list[str]:
        """Return bounded reason tokens without arbitrary exception text."""
        values = set(spider.failure_reasons)
        if self._spider_error:
            values.add("spider_error")
        if self._item_error:
            values.add("item_error")
        if self._item_dropped:
            values.add("item_dropped")
        if self.crawler.stats.get_value("msgloom/lifecycle/close_error_count", 0):
            values.add("framework_close_error")
        if self.crawler.stats.get_value("msgloom/lifecycle/signal_error_count", 0):
            values.add("signal_handler_error")
        if self.crawler.stats.get_value("msgloom/checkpoint/outcome") == "evaluating":
            values.add("checkpoint_evaluation_incomplete")
        if status == "truncated":
            values.add("discovery_truncated")
        elif status == "unverified":
            values.add("completion_unverified")
        if reason != "finished":
            values.add(f"close:{reason}")
        return sorted(
            value if self._safe_reason.fullmatch(value) else "redacted"
            for value in values
            if isinstance(value, str)
        )

    def _common_counts(self) -> tuple[int, int, int, int, int, int]:
        """Return safe framework/provider counters shared by summaries."""
        stats = self.crawler.stats
        return (
            int(stats.get_value("downloader/request_count", 0) or 0),
            int(stats.get_value("downloader/response_count", 0) or 0),
            int(stats.get_value("msgloom/evidence/response_persisted_count", 0) or 0),
            int(stats.get_value("msgloom/crawl/failure_count", 0) or 0),
            int(stats.get_value("msgloom/graph_error_retry/count", 0) or 0),
            int(stats.get_value("msgloom/auth/401_retry_count", 0) or 0),
        )

    def _publish_discovery(self, spider, status: str, reason: str) -> None:
        """Log discovery traversal and persistence counts."""
        stats = self.crawler.stats
        exhausted = bool(
            stats.get_value("msgloom/crawl/discovery/pagination_exhausted", False)
        )
        if stats.get_value("msgloom/crawl/discovery/truncated_count", 0):
            pagination = "truncated"
        elif exhausted:
            pagination = "exhausted"
        else:
            pagination = "unknown"
        stats.set_value("msgloom/final/pagination_outcome", pagination)
        requests, responses, evidence, failures, graph_retries, auth_retries = (
            self._common_counts()
        )
        logger.info(
            "Outlook discovery final summary: status=%s reason=%s run_id=%s "
            "attempt_id=%s scope=%s pages=%s messages=%s persisted=%s "
            "continuations=%s pagination=%s requests=%s responses=%s "
            "evidence=%s failures=%s graph_retries=%s auth_retries=%s",
            status,
            reason,
            spider.run_id,
            self.attempt_id,
            stats.get_value("msgloom/crawl/discovery/scope", "unknown"),
            stats.get_value("msgloom/crawl/discovery/page_count", 0),
            stats.get_value("msgloom/crawl/discovery/message_count", 0),
            stats.get_value("msgloom/catalog/message_item_processed_count", 0),
            stats.get_value("msgloom/crawl/discovery/continuation_count", 0),
            pagination,
            requests,
            responses,
            evidence,
            failures,
            graph_retries,
            auth_retries,
            extra={"spider": spider},
        )

    def _publish_delta(self, spider, status: str, reason: str) -> None:
        """Log delta traversal, reconciliation, and checkpoint outcome."""
        stats = self.crawler.stats
        checkpoint = self._checkpoint_outcome()
        stats.set_value("msgloom/final/checkpoint_outcome", checkpoint)
        if error_stage := stats.get_value("msgloom/checkpoint/error_stage"):
            stats.set_value("msgloom/final/checkpoint_error_stage", error_stage)
        requests, responses, evidence, failures, graph_retries, auth_retries = (
            self._common_counts()
        )
        logger.info(
            "Outlook delta final summary: status=%s reason=%s run_id=%s "
            "attempt_id=%s folders=%s/%s folder_pages=%s message_pages=%s "
            "upserts=%s removals=%s reconciliation=%s reconcile_messages=%s "
            "orphans=%s recovered=%s checkpoint=%s committed_folders=%s "
            "requests=%s responses=%s evidence=%s failures=%s "
            "graph_retries=%s auth_retries=%s",
            status,
            reason,
            spider.run_id,
            self.attempt_id,
            stats.get_value("msgloom/crawl/delta/folder_completed_count", 0),
            stats.get_value("msgloom/crawl/delta/folder_started_count", 0),
            stats.get_value("msgloom/crawl/delta/folder_page_count", 0),
            stats.get_value("msgloom/crawl/delta/message_page_count", 0),
            stats.get_value("msgloom/crawl/delta/message_upsert_count", 0),
            stats.get_value("msgloom/crawl/delta/message_removed_count", 0),
            "completed"
            if stats.get_value("msgloom/crawl/reconcile/completed", False)
            else "pending",
            stats.get_value("msgloom/crawl/reconcile/message_count", 0),
            stats.get_value("msgloom/crawl/reconcile/orphan_count", 0),
            stats.get_value("msgloom/crawl/reconcile/message_recovered_count", 0),
            checkpoint,
            stats.get_value("msgloom/checkpoint/committed_folder_count", 0),
            requests,
            responses,
            evidence,
            failures,
            graph_retries,
            auth_retries,
            extra={"spider": spider},
        )

    def _publish_mail_rule_summary(self, spider) -> None:
        """Log aggregate rule activity without identifiers or control semantics."""
        stats = self.crawler.stats
        evaluated = int(
            stats.get_value("msgloom/crawl/mail_rules/evaluated_count", 0) or 0
        )
        if evaluated <= 0:
            return

        logger.info(
            "Outlook Mail rule summary: event=outlook_mail_rule_summary "
            "evaluated=%s matched=%s default=%s unresolved=%s "
            "probe_scheduled=%s probe_completed=%s probe_failed=%s "
            "stop_processing=%s fallback=%s errors=%s",
            evaluated,
            int(stats.get_value("msgloom/crawl/mail_rules/matched_count", 0) or 0),
            int(stats.get_value("msgloom/crawl/mail_rules/default_count", 0) or 0),
            int(stats.get_value("msgloom/crawl/mail_rules/unresolved_count", 0) or 0),
            int(
                stats.get_value("msgloom/crawl/mail_rules/probe_scheduled_count", 0)
                or 0
            ),
            int(
                stats.get_value("msgloom/crawl/mail_rules/probe_completed_count", 0)
                or 0
            ),
            int(stats.get_value("msgloom/crawl/mail_rules/probe_failed_count", 0) or 0),
            int(
                stats.get_value("msgloom/crawl/mail_rules/stop_processing_count", 0)
                or 0
            ),
            int(stats.get_value("msgloom/crawl/mail_rules/fallback_count", 0) or 0),
            int(
                stats.get_value("msgloom/crawl/mail_rules/evaluation_error_count", 0)
                or 0
            ),
            extra={"spider": spider},
        )

    def _publish_full(self, spider, status: str, reason: str) -> None:
        """Log execution coverage without claiming Full-profile completeness."""
        stats = self.crawler.stats
        stats.set_value("msgloom/final/profile_completeness", "not_evaluated")
        requests, responses, evidence, failures, graph_retries, auth_retries = (
            self._common_counts()
        )
        logger.info(
            "Outlook full final summary: status=%s reason=%s run_id=%s "
            "attempt_id=%s operation=%s profile=%s targets=%s "
            "planner_no_work=%s details=%s mime=%s attachment_pages=%s "
            "attachments=%s attachment_raw=%s item_details=%s "
            "profile_completeness=not_evaluated requests=%s responses=%s "
            "evidence=%s failures=%s graph_retries=%s auth_retries=%s",
            status,
            reason,
            spider.run_id,
            self.attempt_id,
            stats.get_value("msgloom/crawl/enrichment/operation", "unknown"),
            stats.get_value("msgloom/crawl/enrichment/profile", "unknown"),
            stats.get_value("msgloom/crawl/enrichment/target_message_count", 0),
            stats.get_value("msgloom/crawl/enrichment/already_complete_count", 0),
            stats.get_value("msgloom/crawl/enrichment/message_detail_count", 0),
            stats.get_value("msgloom/crawl/enrichment/message_mime_count", 0),
            stats.get_value("msgloom/crawl/enrichment/attachment_page_count", 0),
            stats.get_value("msgloom/crawl/enrichment/attachment_count", 0),
            stats.get_value("msgloom/crawl/enrichment/attachment_raw_count", 0),
            stats.get_value("msgloom/crawl/enrichment/item_attachment_detail_count", 0),
            requests,
            responses,
            evidence,
            failures,
            graph_retries,
            auth_retries,
            extra={"spider": spider},
        )
