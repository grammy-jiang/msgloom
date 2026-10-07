"""Early JOBDIR scope validation for resumable Calendar read spiders."""

from __future__ import annotations

import logging
from typing import Protocol, cast

from scrapy.exceptions import CloseSpider
from scrapy.extensions.spiderstate import SpiderState

from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from message_ingest.spiders.microsoft.outlook.calendar.full import (
    OutlookCalendarFullSpider,
)
from message_ingest.spiders.microsoft.outlook.calendar.window import (
    OutlookCalendarWindowSpider,
)

logger = logging.getLogger(__name__)


class _CalendarResumable(Protocol):
    def _restore_execution_state(self) -> None: ...


class _CalendarScopedSpiderState(SpiderState):
    spider_type = MicrosoftGraphSpider
    reason = "calendar_jobdir_scope_mismatch"

    def spider_opened(self, spider) -> None:
        super().spider_opened(spider)
        if not isinstance(spider, self.spider_type):
            raise TypeError(
                f"{type(self).__name__} requires {self.spider_type.__name__}"
            )
        try:
            cast(_CalendarResumable, spider)._restore_execution_state()
        except (TypeError, ValueError) as exc:
            MicrosoftGraphSpider.mark_run_failed(spider, self.reason)
            logger.error("Cannot resume Calendar JOBDIR: %s", exc)
            raise CloseSpider(reason=self.reason) from exc


class CalendarWindowSpiderState(_CalendarScopedSpiderState):
    """Validate fixed-window acquisition scope before saved Requests execute."""

    spider_type = OutlookCalendarWindowSpider


class CalendarFullSpiderState(_CalendarScopedSpiderState):
    """Validate targeted Full-v1 acquisition scope before saved Requests execute."""

    spider_type = OutlookCalendarFullSpider


__all__ = ["CalendarFullSpiderState", "CalendarWindowSpiderState"]
