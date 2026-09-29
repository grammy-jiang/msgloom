"""Promote To Do absence only after clean, durably complete snapshot idle."""

from __future__ import annotations

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from message_ingest.extensions.catalog import CatalogService
from message_ingest.sync.microsoft.todo.snapshots import TodoSnapshotStore


class TodoSnapshotExtension:
    """Gate authoritative presence promotion on native idle and durable proof."""

    def __init__(self, crawler) -> None:
        """Keep crawler resources; catalog access begins only for sync spiders."""
        self.crawler = crawler
        self.service: CatalogService | None = None
        self.store: TodoSnapshotStore | None = None
        self.base_revision: int | None = None
        self._handled = False

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only for the dedicated authoritative To Do sync spider."""
        if crawler.spidercls.name != "microsoft_todo_sync":
            raise NotConfigured("not an authoritative To Do sync")
        extension = cls(crawler)
        crawler.signals.connect(extension.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(extension.spider_idle, signal=signals.spider_idle)
        return extension

    def spider_opened(self, spider) -> None:
        """Capture the source revision before any authoritative request runs."""
        if not self.crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            spider.mark_run_failed("todo_snapshot_catalog_disabled")
            raise CloseSpider("todo_snapshot_catalog_disabled")
        if not self.crawler.settings.getbool("MSGLOOM_RAW_EVIDENCE_ENABLED"):
            spider.mark_run_failed("todo_snapshot_evidence_disabled")
            raise CloseSpider("todo_snapshot_evidence_disabled")
        source_id = self.crawler.settings.get("MSGLOOM_SOURCE_ID")
        if not isinstance(source_id, str) or not source_id:
            spider.mark_run_failed("todo_snapshot_source_missing")
            raise CloseSpider("todo_snapshot_source_missing")
        try:
            service = CatalogService.from_crawler(self.crawler)
            self.service = service
            self.store = TodoSnapshotStore(service.catalog, source_id=source_id)
            self.base_revision = self.store.load_revision()
        # Any initialization failure invalidates authoritative absence.
        except Exception as exc:
            spider.mark_run_failed("todo_snapshot_initialization_failed")
            spider.logger.error(
                "To Do snapshot initialization failed: error_type=%s",
                type(exc).__name__,
            )
            raise CloseSpider("todo_snapshot_initialization_failed") from exc
        self.crawler.stats.inc_value("msgloom/todo_snapshot/run_started_count")

    def spider_idle(self, spider) -> None:
        """Promote synchronously after native idle proves writes finished."""
        if self._handled:
            return
        if spider.run_failed:
            self._handled = True
            self.crawler.stats.inc_value(
                "msgloom/todo_snapshot/promotion_blocked_count"
            )
            raise CloseSpider("todo_snapshot_incomplete")
        if self.service is None or self.store is None:
            self._handled = True
            spider.mark_run_failed("todo_snapshot_not_initialized")
            raise CloseSpider("todo_snapshot_not_initialized")
        if self.service.write_lock.locked():
            self._handled = True
            spider.mark_run_failed("todo_snapshot_write_busy")
            self.crawler.stats.inc_value(
                "msgloom/todo_snapshot/promotion_blocked_count"
            )
            raise CloseSpider("todo_snapshot_incomplete")

        self._handled = True
        try:
            # Scrapy 2.19 idle excludes pending item pipeline work. With the
            # shared write lock free, promotion finishes before pipeline close
            # can dispose the catalog; no background task can outlive shutdown.
            result = self._stage_and_promote(spider.run_id)
        # Any promotion failure must preserve the previously authoritative
        # state.
        except Exception as exc:
            spider.mark_run_failed("todo_snapshot_promotion_failed")
            self.crawler.stats.inc_value(
                "msgloom/todo_snapshot/promotion_blocked_count"
            )
            spider.logger.error(
                "To Do snapshot promotion blocked: error_type=%s",
                type(exc).__name__,
            )
            raise CloseSpider("todo_snapshot_promotion_failed") from exc
        self.crawler.stats.inc_value("msgloom/todo_snapshot/candidate_count")
        self.crawler.stats.inc_value("msgloom/todo_snapshot/promoted_count")
        self.crawler.stats.set_value(
            "msgloom/todo_snapshot/revision", result["revision"]
        )
        self.crawler.stats.set_value(
            "msgloom/todo_snapshot/present_count", result["present"]
        )
        self.crawler.stats.set_value(
            "msgloom/todo_snapshot/absent_count", result["absent"]
        )

    def _stage_and_promote(self, run_id: str) -> dict[str, int]:
        """Persist terminal proof before the atomic presence promotion."""
        if self.store is None:
            raise RuntimeError("To Do snapshot store is not initialized")
        self.store.stage_candidate(run_id, base_revision=self.base_revision)
        return self.store.promote_snapshot(run_id, base_revision=self.base_revision)


__all__ = ["TodoSnapshotExtension"]
