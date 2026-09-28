"""Shared Microsoft Graph Spider request, evidence, and failure contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import uuid4

import scrapy
from scrapy.http import Response
from scrapy.settings import BaseSettings
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.python.failure import Failure

from message_ingest.items.acquisition import (
    AcquisitionFailureItem,
    RawHttpEvidenceItem,
)
from microsoft_graph.scrapy import MicrosoftGraphSpider as GraphSpider
from microsoft_graph.scrapy.spiders import DefaultPrefer


class MicrosoftGraphSpider(GraphSpider, ABC):
    """
    Adapt reusable Graph acquisition to msgloom evidence and run integrity.

    Resource spiders declare required Graph permissions and own pagination,
    semantic items, and completion rules. This base translates permissions
    into authentication settings and adds raw evidence, terminal request
    failures, and logical run integrity to the framework request API.
    """

    failure_context_keys: ClassVar[tuple[str, ...]] = ()
    graph_permissions: ClassVar[tuple[str, ...]] = ()
    mailbox_targeted: ClassVar[bool] = False

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Translate resource permissions into shared Graph auth settings."""
        settings.set("MS_GRAPH_AUTH_ENABLED", True, priority="spider")
        scopes = cls.required_graph_permissions(settings)
        if scopes:
            settings.set("MS_GRAPH_SCOPES", list(scopes), priority="spider")
        super().update_settings(settings)

    def __init__(self, *args, **kwargs) -> None:
        """Assign a logical run identity and initialize integrity state."""
        super().__init__(*args, **kwargs)
        self.run_id = uuid4().hex
        self._run_failed = False
        self._failure_reasons: set[str] = set()

    @abstractmethod
    async def start(self) -> AsyncIterator[Any]:
        """Yield resource-specific requests and items through Scrapy."""
        async for output in super().start():
            yield output

    def errback(self, failure: Failure) -> Iterator[Any]:
        """Emit exhausted request evidence before the semantic failure item."""
        evidence = self._failure_evidence_item(failure)
        yield evidence
        yield self._request_failure_item(failure, evidence)

    def _failure_evidence_item(self, failure: Failure) -> RawHttpEvidenceItem:
        """
        Retain the final HTTP error response or transport failure.

        Downloader retries occur before this errback. The evidence describes
        the final exchange visible to the Spider, not every transport attempt.
        """
        request = self._failure_request(failure)
        purpose = request.cb_kwargs.get("purpose", "unknown")
        error_type = failure.type.__name__ if failure.type else "UnknownError"
        error_message = failure.getErrorMessage()
        if isinstance(failure.value, HttpError):
            return self._raw_http_evidence_item(
                failure.value.response,
                purpose,
                error_type=error_type,
                error_message=error_message,
            )
        return self._raw_http_failure_item(
            request,
            purpose,
            error_type=error_type,
            error_message=error_message,
        )

    def _request_failure_item(
        self,
        failure: Failure,
        evidence: RawHttpEvidenceItem,
    ) -> AcquisitionFailureItem:
        """Mark integrity failed and retain bounded resource callback context."""
        request = self._failure_request(failure)
        purpose = evidence.purpose
        error_type = failure.type.__name__ if failure.type else "UnknownError"
        context = {
            key: value
            for key in self.failure_context_keys
            if isinstance((value := request.cb_kwargs.get(key)), str) and value
        }
        self.logger.error(
            "Microsoft Graph acquisition request failed: "
            "purpose=%s error_type=%s status=%s",
            purpose,
            error_type,
            evidence.response_status,
        )
        self.mark_run_failed(f"request_failure:{purpose}")
        self.crawler.stats.inc_value("msgloom/crawl/failure_count")
        self.crawler.stats.inc_value(f"msgloom/crawl/failure_purpose_count/{purpose}")
        self.crawler.stats.inc_value(f"msgloom/crawl/failure_type_count/{error_type}")
        return AcquisitionFailureItem(
            url=request.url,
            purpose=purpose,
            error_type=error_type,
            error_message=failure.getErrorMessage(),
            observed_at=evidence.observed_at,
            context=context,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )

    @property
    def run_failed(self) -> bool:
        """Return whether the logical run has an integrity failure."""
        return self._run_failed

    @property
    def failure_reasons(self) -> frozenset[str]:
        """Expose bounded integrity reason tokens without mutable state."""
        return frozenset(self._failure_reasons)

    def mark_run_failed(self, reason: str) -> None:
        """Record one logical-run integrity failure reason."""
        if reason in self._failure_reasons:
            return
        self._run_failed = True
        self._failure_reasons.add(reason)
        self.crawler.stats.inc_value(
            f"msgloom/crawl/integrity_failure_reason_count/{reason}"
        )

    def _max_raw_content_bytes(self) -> int:
        """Return the configured binary/raw-response cap; zero means unlimited."""
        value = self.crawler.settings.getint("MSGLOOM_MAX_RAW_CONTENT_BYTES", 0)
        if value < 0:
            raise ValueError("MSGLOOM_MAX_RAW_CONTENT_BYTES must be >= 0")
        return value

    def _attachment_size_exceeds_limit(self, size: object) -> bool:
        limit = self._max_raw_content_bytes()
        return (
            limit > 0
            and isinstance(size, int)
            and not isinstance(size, bool)
            and size > limit
        )

    def _request(
        self,
        url: str,
        *,
        callback,
        purpose: str,
        cb_kwargs: dict[str, Any],
        verbatim_url: bool = False,
        accept: str = "application/json",
        dont_cache: bool = False,
        prefer: str | None | DefaultPrefer = DefaultPrefer.VALUE,
        download_maxsize: int | None = None,
    ) -> scrapy.Request:
        """
        Build a serializable Graph request with explicit callback context.

        Provider continuation URLs may be opaque. Resource-specific Prefer
        headers are opt-in; this provider base does not assume Outlook
        immutable-ID semantics.
        """
        return self.graph_request(
            url,
            callback=callback,
            errback=self.errback,
            operation=purpose,
            cb_kwargs={**cb_kwargs, "purpose": purpose},
            verbatim_url=verbatim_url,
            accept=accept,
            prefer=prefer,
            dont_cache=dont_cache,
            download_maxsize=download_maxsize,
        )

    @staticmethod
    def _failure_request(failure: Failure) -> scrapy.Request:
        """Return the Scrapy Request attached to a downloader failure."""
        request = getattr(failure, "request", None)
        if not isinstance(request, scrapy.Request):
            raise TypeError("Scrapy request failure must carry a Request")
        return request

    def _raw_http_evidence_item(
        self,
        response: Response,
        purpose: str,
        *,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> RawHttpEvidenceItem:
        """
        Capture a linked response with credentials removed from headers.

        A fresh evidence ID is provisional: cache replay may resolve it to an
        older capture before semantic items reach their resource catalog.
        """
        if (request := response.request) is None:
            raise ValueError(
                "HTTP evidence requires a response linked to its Scrapy request"
            )
        origin = "http_cache" if "cached" in response.flags else "network"
        observed_at = self._response_observed_at(response)
        return RawHttpEvidenceItem(
            evidence_id=uuid4().hex,
            run_id=self.run_id,
            purpose=purpose,
            observed_at=observed_at,
            origin=origin,
            request_fingerprint=self.crawler.request_fingerprinter.fingerprint(
                request
            ).hex(),
            request_url=request.url,
            request_method=request.method,
            request_headers=self._headers_for_evidence(request.headers),
            request_body=request.body,
            response_url=response.url,
            response_status=response.status,
            response_headers=self._headers_for_evidence(response.headers),
            response_body=response.body,
            response_flags=list(response.flags),
            error_type=error_type,
            error_message=error_message,
        )

    def _raw_http_failure_item(
        self,
        request: scrapy.Request,
        purpose: str,
        *,
        error_type: str,
        error_message: str,
    ) -> RawHttpEvidenceItem:
        """Capture a failed request without inventing an HTTP response."""
        return RawHttpEvidenceItem(
            evidence_id=uuid4().hex,
            run_id=self.run_id,
            purpose=purpose,
            observed_at=datetime.now(UTC).isoformat(),
            origin="download_error",
            request_fingerprint=self.crawler.request_fingerprinter.fingerprint(
                request
            ).hex(),
            request_url=request.url,
            request_method=request.method,
            request_headers=self._headers_for_evidence(request.headers),
            request_body=request.body,
            response_url=None,
            response_status=None,
            response_headers={},
            response_body=b"",
            response_flags=[],
            error_type=error_type,
            error_message=error_message,
        )

    @staticmethod
    def _response_observed_at(response: Response) -> str:
        """Preserve a valid cache capture time or use the current UTC time."""
        if "cached" in response.flags:
            cache_timestamp = response.meta.get("cache_timestamp")
            if cache_timestamp is not None:
                try:
                    return datetime.fromtimestamp(
                        float(cache_timestamp),
                        UTC,
                    ).isoformat()
                except (TypeError, ValueError, OverflowError):
                    pass
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _headers_for_evidence(headers) -> dict[str, list[str]]:
        """Preserve multi-value headers while excluding credentials."""
        result: dict[str, list[str]] = {}
        for raw_name in headers:
            name = (
                raw_name.decode("latin-1")
                if isinstance(raw_name, bytes)
                else str(raw_name)
            )
            if name.lower() in {"authorization", "proxy-authorization"}:
                continue
            result[name] = [
                value.decode("latin-1") if isinstance(value, bytes) else str(value)
                for value in headers.getlist(raw_name)
            ]
        return result
