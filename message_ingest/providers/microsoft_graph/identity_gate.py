"""Gate persisted Microsoft Graph acquisition on verified source identity."""

from __future__ import annotations

import logging
import os

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from message_ingest.acquisition.source_identity import (
    SourceIdentityBootstrapRequired,
    SourceIdentityError,
)
from message_ingest.providers.microsoft_graph.accounts import (
    MicrosoftGraphAuthError,
)
from message_ingest.providers.microsoft_graph.auth_session import (
    MicrosoftGraphAuthSession,
)
from message_ingest.providers.microsoft_graph.spider import (
    MicrosoftGraphSpider,
)

logger = logging.getLogger(__name__)


class MicrosoftGraphSourceIdentityExtension:
    """Verify the bound account before Scheduler requests execute."""

    def __init__(self, crawler) -> None:
        """Keep crawler resources for startup gate stats and auth session."""
        self.crawler = crawler

    @classmethod
    def from_crawler(cls, crawler):
        """Enable the gate only for catalog-backed Graph resources."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Source identity persistence is disabled")
        extension = cls(crawler)
        crawler.signals.connect(
            extension.spider_opened, signal=signals.spider_opened
        )
        return extension

    async def spider_opened(self, spider) -> None:
        """Fail before requests run when source identity is unverified."""
        if not isinstance(spider, MicrosoftGraphSpider):
            return
        if os.getenv("SCRAPY_CHECK") == "true":
            self.crawler.stats.set_value(
                "msgloom/source_identity/gate_state",
                "contract_check_skipped",
            )
            return
        if not self.crawler.settings.getbool(
            "MSGLOOM_SOURCE_IDENTITY_REQUIRED"
        ):
            self.crawler.stats.set_value(
                "msgloom/source_identity/gate_state", "disabled"
            )
            return

        method = self.crawler.settings.get(
            "MS_GRAPH_AUTH_METHOD", "device_code"
        ).strip().lower()
        if method not in {"device_code", "interactive"}:
            self._fail(spider, "AuthenticationDisabled")

        try:
            session = MicrosoftGraphAuthSession.from_crawler(self.crawler)
            await session.establish_source_identity()
        except CloseSpider:
            raise
        except SourceIdentityBootstrapRequired:
            logger.error(
                "Legacy source identity requires explicit one-run "
                "confirmation: "
                "-s MSGLOOM_SOURCE_IDENTITY_BOOTSTRAP_CONFIRM="
                "<configured-source-id>",
                extra={"spider": spider},
            )
            self._fail(
                spider,
                "SourceIdentityBootstrapRequired",
                log_error=False,
            )
        except (MicrosoftGraphAuthError, SourceIdentityError) as exc:
            self._fail(
                spider,
                type(exc).__name__,
                detail=str(exc),
            )
        except Exception as exc:
            self._fail(spider, type(exc).__name__)

    def _fail(
        self,
        spider: MicrosoftGraphSpider,
        error_type: str,
        *,
        log_error: bool = True,
        detail: str | None = None,
    ) -> None:
        """Record a bounded startup failure and request controlled close."""
        # Call the provider base deliberately. OutlookDeltaSpider overrides
        # mark_run_failed() by persisting Spider.state, but startup identity
        # failure may happen before SpiderState has restored the JOBDIR state.
        # Calling the base avoids overwriting a valid resume snapshot.
        MicrosoftGraphSpider.mark_run_failed(spider, "source_identity_failed")
        self.crawler.stats.inc_value(
            "msgloom/source_identity/gate_failed_count"
        )
        self.crawler.stats.set_value(
            "msgloom/source_identity/gate_state", "failed"
        )
        if log_error and detail is not None:
            logger.error(
                "Microsoft Graph source identity gate failed: "
                "error_type=%s detail=%s",
                error_type,
                detail,
                extra={"spider": spider},
            )
        elif log_error:
            logger.error(
                "Microsoft Graph source identity gate failed: error_type=%s",
                error_type,
                extra={"spider": spider},
            )
        raise CloseSpider(reason="source_identity_failed")
