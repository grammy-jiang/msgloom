"""Gate persisted Microsoft Graph acquisition on verified source identity."""

from __future__ import annotations

import logging
import os

from scrapy import signals
from scrapy.exceptions import CloseSpider, NotConfigured

from message_ingest.acquisition.source_identity import (
    SourceIdentity,
    SourceIdentityBootstrapRequired,
    SourceIdentityError,
    SourceIdentityService,
)
from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from microsoft_graph import PROVIDER_ID
from microsoft_graph.auth.accounts import (
    ACCOUNT_KEY_SCHEME,
    MicrosoftGraphAuthError,
)
from microsoft_graph.auth.session import MicrosoftGraphAuthSession

logger = logging.getLogger(__name__)


class _SourceIdentityAccountBinding:
    """Adapt msgloom source identity storage to the Graph auth protocol."""

    def __init__(self, service: SourceIdentityService) -> None:
        self.service = service
        self._binding = service.get_binding()

    @property
    def write_lock(self):
        """Reuse the catalog-scoped lock for first-binding serialization."""
        return self.service.service.write_lock

    def has_binding(self) -> bool:
        """Refresh and report whether this source already has an account binding."""
        self._binding = self.service.get_binding()
        return self._binding is not None

    @staticmethod
    def _identity(account_key: str) -> SourceIdentity:
        return SourceIdentity(
            provider=PROVIDER_ID,
            key_scheme=ACCOUNT_KEY_SCHEME,
            account_key=account_key,
        )

    def matches_account_key(self, account_key: str) -> bool:
        """Match one opaque account key without exposing it to persistence."""
        binding = self._binding
        if binding is None:
            binding = self.service.get_binding()
            self._binding = binding
        return self.service.matches_binding(self._identity(account_key), binding)

    def bind_or_verify_account_key(self, account_key: str) -> str:
        """Bind or verify one opaque account key through msgloom persistence."""
        outcome = self.service.bind_or_verify(self._identity(account_key))
        self._binding = self.service.get_binding()
        return outcome


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
        crawler.signals.connect(extension.spider_opened, signal=signals.spider_opened)
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
        if not self.crawler.settings.getbool("MSGLOOM_SOURCE_IDENTITY_REQUIRED"):
            self.crawler.stats.set_value(
                "msgloom/source_identity/gate_state", "disabled"
            )
            return

        method = (
            self.crawler.settings.get("MS_GRAPH_AUTH_METHOD", "device_code")
            .strip()
            .lower()
        )
        if method not in {"device_code", "interactive"}:
            self._fail(spider, "AuthenticationDisabled")

        try:
            service = SourceIdentityService.from_crawler(self.crawler)
            session = MicrosoftGraphAuthSession.from_crawler(self.crawler)
            session.attach_account_binding(_SourceIdentityAccountBinding(service))
            await session.establish_account_binding()
            self.crawler.stats.set_value(
                "msgloom/source_identity/gate_state",
                "verified",
            )
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
        # Fail closed on unexpected startup failures without logging provider data.
        except Exception as exc:  # noqa: BLE001
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
        self.crawler.stats.inc_value("msgloom/source_identity/gate_failed_count")
        self.crawler.stats.set_value("msgloom/source_identity/gate_state", "failed")
        if log_error and detail is not None:
            logger.error(
                "Microsoft Graph source identity gate failed: error_type=%s detail=%s",
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
