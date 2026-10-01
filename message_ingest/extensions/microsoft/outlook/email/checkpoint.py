"""Commit complete delta rounds after Scrapy finishes all item processing."""

from __future__ import annotations

import logging

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.spiders.microsoft.outlook.email._delta_state import (
    MailDeltaCommitMode,
)
from message_ingest.spiders.microsoft.outlook.email.delta import OutlookDeltaSpider
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)
from message_ingest.sync.microsoft.outlook.email.promotion import (
    promote_validated_mail_delta,
    validate_mail_delta_run,
)

logger = logging.getLogger(__name__)


class OutlookDeltaCheckpointExtension:
    """
    Commit a delta round only after Scrapy reports a complete, clean idle.
    """

    def __init__(self, crawler) -> None:
        """
        Borrow checkpoint storage and remember which runs already passed the
        idle gate.
        """
        self.crawler = crawler
        service = CatalogService.from_crawler(crawler)
        self.store = OutlookDeltaCheckpointStore(
            service.catalog, crawler.settings["MSGLOOM_SOURCE_ID"]
        )
        self.lifecycle = OutlookMailStore(
            service.catalog,
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
        )
        self._handled_run_ids: set[str] = set()

    @classmethod
    def from_crawler(cls, crawler):
        """
        Register native lifecycle/error signals only when catalog-backed
        checkpoints are enabled.
        """
        if not crawler.settings.getbool("MSGLOOM_DELTA_CHECKPOINT_ENABLED"):
            raise NotConfigured("Outlook delta checkpoint extension disabled")
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Delta checkpoints require the SQLAlchemy catalog")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_idle, signal=signals.spider_idle)
        crawler.signals.connect(extension.spider_error, signal=signals.spider_error)
        crawler.signals.connect(extension.item_error, signal=signals.item_error)
        crawler.signals.connect(extension.item_dropped, signal=signals.item_dropped)
        return extension

    def spider_error(self, spider, **_kwargs) -> None:
        """
        Callback exceptions bypass request errbacks; mark delta integrity
        failed here.
        """
        if isinstance(spider, OutlookDeltaSpider):
            spider.mark_run_failed("spider_error")

    def item_error(self, spider, **_kwargs) -> None:
        """Treat any failed persistence stage as a delta integrity failure."""
        if isinstance(spider, OutlookDeltaSpider):
            spider.mark_run_failed("item_error")

    def item_dropped(self, spider, **_kwargs) -> None:
        """
        A dropped item can leave evidence incomplete, so block delta promotion.
        """
        if isinstance(spider, OutlookDeltaSpider):
            spider.mark_run_failed("item_dropped")

    def spider_idle(self, spider) -> None:
        """
        Validate exact completion sets and atomically promote this run's
        cursors.

        Scrapy 2.19 idle excludes pending pipeline work. This signal does not
        await async handlers, so commit synchronously here. Stats explain the
        result; execution facts and persisted candidates decide whether it is
        safe. A normal close alone is not proof of a complete round. Raise
        :exc:`~scrapy.exceptions.CloseSpider` with a specific failure reason.
        """
        if not isinstance(spider, OutlookDeltaSpider):
            return
        run_id = getattr(spider, "run_id", "")
        if not run_id or run_id in self._handled_run_ids:
            return
        self._handled_run_ids.add(run_id)

        stats = self.crawler.stats
        stats.set_value("msgloom/checkpoint/outcome", "evaluating")
        try:
            snapshot = spider.delta_execution_snapshot()
        except Exception as exc:
            stats.inc_value("msgloom/checkpoint/error_count")
            stats.set_value("msgloom/checkpoint/outcome", "error")
            stats.set_value("msgloom/checkpoint/error_stage", "snapshot")
            spider.mark_run_failed("checkpoint_evaluation_failed")
            logger.error(
                "Unable to evaluate Outlook delta checkpoint state: error_type=%s",
                type(exc).__name__,
                extra={"spider": spider},
            )
            raise CloseSpider(reason="checkpoint_evaluation_failed") from exc

        started = snapshot["started_folder_ids"]
        completed = snapshot["completed_folder_ids"]
        try:
            candidates = self.store.load_candidates(run_id)
        except Exception as exc:
            stats.inc_value("msgloom/checkpoint/error_count")
            stats.inc_value("msgloom/checkpoint/candidate_read_error_count")
            stats.set_value("msgloom/checkpoint/outcome", "error")
            stats.set_value("msgloom/checkpoint/error_stage", "candidate_load")
            spider.mark_run_failed("checkpoint_candidate_load_failed")
            logger.error(
                "Unable to load Outlook delta checkpoint candidates: error_type=%s",
                type(exc).__name__,
                extra={"spider": spider},
            )
            raise CloseSpider(reason="checkpoint_candidate_load_failed") from exc

        try:
            validated = validate_mail_delta_run(snapshot, candidates)
        except ValueError:
            candidate_ids = set(candidates)
            stats.inc_value("msgloom/checkpoint/commit_skipped_count")
            stats.set_value("msgloom/checkpoint/outcome", "skipped")
            stats.set_value("msgloom/checkpoint/expected_folder_count", len(started))
            stats.set_value("msgloom/checkpoint/completed_folder_count", len(completed))
            stats.set_value(
                "msgloom/checkpoint/candidate_folder_count", len(candidate_ids)
            )
            stats.set_value(
                "msgloom/checkpoint/integrity_failure_reason_count",
                len(snapshot["failure_reasons"]),
            )
            logger.warning(
                "Outlook delta checkpoint commit skipped: "
                "run_id=%s started=%s completed=%s candidates=%s failures=%s",
                run_id,
                len(started),
                len(completed),
                len(candidate_ids),
                sorted(snapshot["failure_reasons"]),
                extra={"spider": spider},
            )
            raise CloseSpider(reason="delta_incomplete") from None

        mode = spider.mail_delta_commit_mode
        if mode is MailDeltaCommitMode.DEFERRED:
            spider._validated_delta_run = validated
            stats.set_value("msgloom/checkpoint/outcome", "deferred")
            stats.set_value(
                "msgloom/checkpoint/expected_folder_count",
                len(validated.expected_folder_ids),
            )
            stats.set_value(
                "msgloom/checkpoint/completed_folder_count",
                len(validated.expected_folder_ids),
            )
            stats.set_value(
                "msgloom/checkpoint/candidate_folder_count",
                len(validated.candidate_folder_ids),
            )
            logger.info(
                "Outlook delta checkpoint promotion deferred: run_id=%s folders=%s",
                run_id,
                len(validated.candidate_folder_ids),
                extra={"spider": spider},
            )
            return

        if mode is MailDeltaCommitMode.BLOCKED:
            stats.inc_value("msgloom/checkpoint/commit_skipped_count")
            stats.set_value("msgloom/checkpoint/outcome", "skipped")
            stats.set_value(
                "msgloom/checkpoint/expected_folder_count",
                len(validated.expected_folder_ids),
            )
            stats.set_value(
                "msgloom/checkpoint/completed_folder_count",
                len(validated.expected_folder_ids),
            )
            stats.set_value(
                "msgloom/checkpoint/candidate_folder_count",
                len(validated.candidate_folder_ids),
            )
            raise CloseSpider(reason="policy_completion_required")

        try:
            outcome = promote_validated_mail_delta(
                self.store.catalog,
                source_id=self.store.source_id,
                validated=validated,
            )
            committed = outcome["committed_folders"]
            stats.set_value(
                "msgloom/catalog/folder_presence_present_count",
                outcome["folders_present"],
            )
            stats.set_value(
                "msgloom/catalog/folder_presence_absent_count",
                outcome["folders_absent"],
            )
            stats.set_value(
                "msgloom/catalog/message_presence_present_count",
                outcome["messages_present"],
            )
            stats.set_value(
                "msgloom/catalog/message_presence_absent_count",
                outcome["messages_absent"],
            )
        except Exception as exc:
            stats.inc_value("msgloom/checkpoint/error_count")
            stats.inc_value("msgloom/checkpoint/commit_error_count")
            stats.set_value("msgloom/checkpoint/outcome", "error")
            stats.set_value("msgloom/checkpoint/error_stage", "commit")
            spider.mark_run_failed("checkpoint_commit_failed")
            logger.error(
                "Unable to commit Outlook delta checkpoints: error_type=%s",
                type(exc).__name__,
                extra={"spider": spider},
            )
            raise CloseSpider(reason="checkpoint_commit_failed") from exc

        stats.inc_value("msgloom/checkpoint/commit_count")
        stats.set_value("msgloom/checkpoint/outcome", "committed")
        stats.set_value("msgloom/checkpoint/committed_folder_count", committed)
        logger.info(
            "Outlook delta checkpoints committed: run_id=%s folders=%s",
            run_id,
            committed,
            extra={"spider": spider},
        )
