"""Promote complete Microsoft Calendar delta rounds at Spider idle."""

from __future__ import annotations

import logging

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured
from scrapy.extensions.spiderstate import SpiderState

from message_ingest.calendar_checkpoints import CalendarDeltaCheckpointStore
from message_ingest.providers.microsoft_graph.spider import MicrosoftGraphSpider
from message_ingest.spiders.microsoft.outlook.calendar.delta import (
    OutlookCalendarDeltaSpider,
)

logger = logging.getLogger(__name__)


class CalendarDeltaSpiderState(SpiderState):
    """
    Validate restored state before Scrapy starts dequeuing saved requests.

    Native SpiderState owns serialization. Load and validation share a handler
    because Scrapy does not order handlers of the same signal. A rejected open
    leaves the saved execution facts intact for a correctly scoped resume.
    """

    def spider_opened(self, spider) -> None:
        super().spider_opened(spider)
        if not isinstance(spider, OutlookCalendarDeltaSpider):
            raise TypeError("Calendar SpiderState requires a Calendar delta spider")
        try:
            spider._restore_execution_state()
        except (TypeError, ValueError) as exc:
            MicrosoftGraphSpider.mark_run_failed(
                spider, "calendar_jobdir_scope_mismatch"
            )
            logger.error("Cannot resume Calendar JOBDIR: %s", exc)
            raise CloseSpider(reason="calendar_jobdir_scope_mismatch") from exc


class CalendarDeltaCheckpointExtension:
    """Commit one fixed-window Calendar cursor only after complete idle."""

    def __init__(self, crawler) -> None:
        self.crawler = crawler
        self._handled: set[tuple[str, int]] = set()

    @classmethod
    def from_crawler(cls, crawler):
        """Enable only for the Calendar delta spider's explicit setting."""
        if not crawler.settings.getbool("MSGLOOM_CALENDAR_DELTA_CHECKPOINT_ENABLED"):
            raise NotConfigured("Calendar delta checkpoint extension disabled")
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured(
                "Calendar delta checkpoints require the SQLAlchemy catalog"
            )
        extension = cls(crawler)
        crawler.signals.connect(
            extension.spider_idle,
            signal=signals.spider_idle,
        )
        crawler.signals.connect(
            extension.spider_error,
            signal=signals.spider_error,
        )
        crawler.signals.connect(
            extension.item_error,
            signal=signals.item_error,
        )
        crawler.signals.connect(
            extension.item_dropped,
            signal=signals.item_dropped,
        )
        return extension

    @staticmethod
    def _is_calendar_delta(spider) -> bool:
        return isinstance(spider, OutlookCalendarDeltaSpider)

    def spider_error(self, spider, **_kwargs) -> None:
        if self._is_calendar_delta(spider):
            spider.mark_run_failed("spider_error")

    def item_error(self, spider, **_kwargs) -> None:
        if self._is_calendar_delta(spider):
            spider.mark_run_failed("item_error")

    def item_dropped(self, spider, **_kwargs) -> None:
        if self._is_calendar_delta(spider):
            spider.mark_run_failed("item_dropped")

    def spider_idle(self, spider) -> None:
        """
        Validate the terminal candidate after all pipeline work has finished.

        Scrapy 2.19's idle condition excludes pending request and item work, so
        the durable candidate and Spider integrity facts can now decide whether
        the provider cursor is safe to promote.
        """
        if not self._is_calendar_delta(spider):
            return

        snapshot = spider.delta_execution_snapshot()
        run_id = snapshot["run_id"]
        attempt = snapshot["attempt"]
        key = (run_id, attempt)
        if not run_id or key in self._handled:
            return
        self._handled.add(key)

        stats = self.crawler.stats
        stats.set_value(
            "msgloom/calendar/checkpoint/outcome",
            "evaluating",
        )

        store = CalendarDeltaCheckpointStore.from_crawler(
            self.crawler,
            start_datetime=spider.start_datetime,
            end_datetime=spider.end_datetime,
            calendar_scope=spider.calendar_scope,
        )
        try:
            candidate = store.load_candidate(
                run_id=run_id,
                attempt=attempt,
            )
        except Exception as exc:
            stats.set_value(
                "msgloom/calendar/checkpoint/outcome",
                "error",
            )
            stats.inc_value("msgloom/calendar/checkpoint/candidate_read_error_count")
            spider.mark_run_failed("calendar_checkpoint_candidate_load_failed")
            logger.error(
                "Unable to load Calendar delta checkpoint candidate: error_type=%s",
                type(exc).__name__,
                extra={"spider": spider},
            )
            raise CloseSpider(
                reason="calendar_checkpoint_candidate_load_failed"
            ) from exc

        candidate_matches = (
            candidate is not None
            and candidate.base_revision == snapshot["base_revision"]
        )
        if (
            snapshot["run_failed"]
            or not snapshot["terminal_delta_seen"]
            or not candidate_matches
        ):
            stats.set_value(
                "msgloom/calendar/checkpoint/outcome",
                "skipped",
            )
            stats.inc_value("msgloom/calendar/checkpoint/commit_skipped_count")
            spider.mark_run_failed("calendar_delta_incomplete")
            logger.warning(
                "Calendar delta checkpoint commit skipped: run_id=%s "
                "attempt=%s terminal=%s candidate=%s failures=%s",
                run_id,
                attempt,
                snapshot["terminal_delta_seen"],
                candidate is not None,
                sorted(snapshot["failure_reasons"]),
                extra={"spider": spider},
            )
            raise CloseSpider(reason="calendar_delta_incomplete")

        try:
            state = store.commit(
                run_id=run_id,
                attempt=attempt,
            )
        except Exception as exc:
            stats.set_value(
                "msgloom/calendar/checkpoint/outcome",
                "error",
            )
            stats.inc_value("msgloom/calendar/checkpoint/commit_error_count")
            spider.mark_run_failed("calendar_checkpoint_commit_failed")
            logger.error(
                "Unable to commit Calendar delta checkpoint: error_type=%s",
                type(exc).__name__,
                extra={"spider": spider},
            )
            raise CloseSpider(reason="calendar_checkpoint_commit_failed") from exc

        stats.set_value(
            "msgloom/calendar/checkpoint/outcome",
            "committed",
        )
        stats.set_value(
            "msgloom/calendar/checkpoint/revision",
            state.revision,
        )
        stats.inc_value("msgloom/calendar/checkpoint/commit_count")
        logger.info(
            "Calendar delta checkpoint committed: run_id=%s attempt=%s revision=%s",
            run_id,
            attempt,
            state.revision,
            extra={"spider": spider},
        )
