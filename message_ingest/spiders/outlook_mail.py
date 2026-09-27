"""Shared contracts and HTTP evidence for Outlook acquisition spiders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any, ClassVar
from uuid import uuid4

import scrapy
from scrapy.http import Response
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.python.failure import Failure

from message_ingest.items import (
    AcquisitionFailureItem,
    OutlookMailItem,
    RawHttpEvidenceItem,
)


class OutlookMailSpider(scrapy.Spider, ABC):
    """
    Shared Graph requests, evidence, and failures for all three modes.

    Callbacks emit raw evidence before items that reference it. With the
    configured ``CONCURRENT_ITEMS=1``, Scrapy finishes each output before
    consuming the next output from that callback. Pipelines also serialize
    writes across concurrent callbacks. Keep callbacks bound to the spider so
    ``JOBDIR`` can serialize their names.
    """

    allowed_domains: ClassVar[list[str]] = ["graph.microsoft.com"]
    graph_root = "https://graph.microsoft.com/v1.0"

    discovery_fields = (
        "id",
        "subject",
        "from",
        "sender",
        "toRecipients",
        "ccRecipients",
        "bccRecipients",
        "replyTo",
        "receivedDateTime",
        "sentDateTime",
        "createdDateTime",
        "lastModifiedDateTime",
        "importance",
        "isRead",
        "isDraft",
        "hasAttachments",
        "conversationId",
        "conversationIndex",
        "inferenceClassification",
        "flag",
        "categories",
        "bodyPreview",
        "parentFolderId",
        "webLink",
        "internetMessageId",
    )

    def __init__(self, *args, **kwargs) -> None:
        """
        Assign a new run identity; the delta spider may restore one from
        ``JOBDIR``.
        """
        super().__init__(*args, **kwargs)
        self.run_id = uuid4().hex
        self._run_failed = False
        self._failure_reasons: set[str] = set()

    @abstractmethod
    async def start(self) -> AsyncIterator[Any]:
        """
        Yield this mode's requests and items through Scrapy's async interface.
        """
        # Keep the native async-generator signature even on the abstract base.
        async for output in super().start():
            yield output

    def errback(self, failure: Failure) -> Iterator[Any]:
        """
        Emit the exhausted request evidence before its semantic failure item.
        """
        evidence = self._failure_evidence_item(failure)
        yield evidence
        yield self._request_failure_item(failure, evidence)

    def _failure_evidence_item(self, failure: Failure) -> RawHttpEvidenceItem:
        """
        Retain an HTTP error response when available, otherwise record
        transport failure.

        Downloader retries occur before this errback. This evidence describes
        the final exchange visible to the spider, not every transport attempt.
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
        self, failure: Failure, evidence: RawHttpEvidenceItem
    ) -> AcquisitionFailureItem:
        """
        Mark run integrity failed and link the failure to its persisted
        exchange.
        """
        request = self._failure_request(failure)
        callback_data = request.cb_kwargs
        purpose = evidence.purpose
        error_type = failure.type.__name__ if failure.type else "UnknownError"
        self.logger.error(
            "Outlook acquisition request failed: purpose=%s error_type=%s status=%s",
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
            message_id=callback_data.get("message_id"),
            attachment_id=callback_data.get("attachment_id"),
            folder_id=callback_data.get("folder_id"),
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )

    @property
    def run_failed(self) -> bool:
        """Return whether the current logical run has an integrity failure."""
        return self._run_failed

    @property
    def failure_reasons(self) -> frozenset[str]:
        """Expose bounded integrity reason tokens without mutable state."""
        return frozenset(self._failure_reasons)

    def mark_run_failed(self, reason: str) -> None:
        """Record a run integrity failure independently of crawl statistics."""
        if reason in self._failure_reasons:
            return
        self._run_failed = True
        self._failure_reasons.add(reason)
        self.crawler.stats.inc_value(
            f"msgloom/crawl/integrity_failure_reason_count/{reason}"
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
        prefer: str | None = 'IdType="ImmutableId"',
    ) -> scrapy.Request:
        """
        Build a serializable Graph request with this spider's error policy.

        Callback arguments describe business context. Metadata carries only
        component controls; copying arbitrary parent metadata could leak retry
        or cache state. Continuation URLs are supplied by Graph without
        rebuilding their query.
        """
        headers = {"Accept": accept}
        if prefer is not None:
            headers["Prefer"] = prefer
        meta = {}
        if verbatim_url:
            meta["verbatim_url"] = True
        if dont_cache:
            meta["dont_cache"] = True
        return scrapy.Request(
            url,
            callback=callback,
            errback=self.errback,
            headers=headers,
            cb_kwargs={**cb_kwargs, "purpose": purpose},
            meta=meta,
        )

    @staticmethod
    def _failure_request(failure: Failure) -> scrapy.Request:
        """
        Validate the request attribute that Scrapy adds to Twisted failures.
        """
        request = getattr(failure, "request", None)
        if not isinstance(request, scrapy.Request):
            raise TypeError("Scrapy request failure must carry a Request")
        return request

    def _message_item(
        self,
        message: dict[str, Any],
        source_response_url: str,
        observed_at: str,
        *,
        observation_kind: str,
        evidence_id: str | None,
    ) -> OutlookMailItem:
        """
        Retain the complete Graph payload beside searchable discovery fields.
        """
        return OutlookMailItem(
            message_id=message["id"],
            subject=message.get("subject"),
            sender_address=self._email_address(message.get("sender")),
            from_address=self._email_address(message.get("from")),
            received_date_time=message.get("receivedDateTime"),
            internet_message_id=message.get("internetMessageId"),
            conversation_id=message.get("conversationId"),
            parent_folder_id=message.get("parentFolderId"),
            importance=message.get("importance"),
            inference_classification=message.get("inferenceClassification"),
            is_read=message.get("isRead"),
            has_attachments=message.get("hasAttachments"),
            body_preview=message.get("bodyPreview"),
            raw=message,
            source_response_url=source_response_url,
            observed_at=observed_at,
            observation_kind=observation_kind,
            evidence_id=evidence_id,
            run_id=self.run_id,
        )

    def _raw_http_evidence_item(
        self,
        response: Response,
        purpose: str,
        *,
        error_type: str | None = None,
        error_message: str | None = None,
    ) -> RawHttpEvidenceItem:
        """
        Capture a linked response and redact credentials before persistence.

        A fresh evidence ID is provisional: cache replay may resolve it to an
        older capture in
        :class:`~message_ingest.pipelines.evidence.RawEvidencePipeline` before
        semantic items reach the catalog.
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
        """
        Capture a failed request without inventing a response body or HTTP
        status.
        """
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
        """
        Keep valid cache capture time so replay cannot appear newer than live
        data.

        Missing or invalid cache timestamps fall back to the current UTC
        observation. The evidence pipeline can still replace this with an
        existing capture time.
        """
        if "cached" in response.flags:
            cache_timestamp = response.meta.get("cache_timestamp")
            if cache_timestamp is not None:
                try:
                    return datetime.fromtimestamp(
                        float(cache_timestamp), UTC
                    ).isoformat()
                except (TypeError, ValueError, OverflowError):
                    pass
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _headers_for_evidence(headers) -> dict[str, list[str]]:
        """
        Preserve multi-value headers and byte values, excluding authorization
        secrets.
        """
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

    @staticmethod
    def _email_address(recipient: dict[str, Any] | None) -> str | None:
        """
        Accept a missing sender and return the optional nested Graph email
        address.
        """
        if not recipient:
            return None
        return (recipient.get("emailAddress") or {}).get("address")

    @staticmethod
    def _bounded_int(
        raw: str,
        *,
        name: str,
        minimum: int,
        maximum: int | None = None,
    ) -> int:
        """
        Validate string spider arguments before any requests can be scheduled.
        """
        value = int(raw)
        if value < minimum or (maximum is not None and value > maximum):
            upper = f" and <= {maximum}" if maximum is not None else ""
            raise ValueError(f"{name} must be >= {minimum}{upper}")
        return value
