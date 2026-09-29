"""Capture content only for explicit OneDrive IDs, with private URL handling."""

import json
from collections.abc import AsyncIterator, Iterator
from hashlib import sha256
from typing import Any

from scrapy.http import Response
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.python.failure import Failure

from message_ingest.items.acquisition import AcquisitionFailureItem, RawHttpEvidenceItem
from message_ingest.items.microsoft.onedrive import OneDriveContentItem

from ._base import OneDriveSpider

# Location, Content-Location, Link, Refresh, Set-Cookie, and arbitrary vendor
# headers may expose credentials or download URLs. Retain entity facts only.
_ENTITY_HEADERS = frozenset(
    {
        "content-type",
        "content-length",
        "content-encoding",
        "content-range",
        "last-modified",
        "date",
        "etag",
        "accept-ranges",
        "retry-after",
    }
)


class MicrosoftOneDriveContentSpider(OneDriveSpider):
    """
    Use native redirects and persist binary bytes only as raw HTTP evidence.

    The original request allows offsite redirects. Scrapy removes cross-origin
    Authorization; the Graph auth middleware also removes Graph credentials
    before redirect processing and never authenticates a non-Graph host.
    Download URLs live only in transport requests, never semantic evidence
    URLs or headers. Callback context contains raw item IDs, not download URLs.
    """

    name = "microsoft_onedrive_content"

    def __init__(self, *args, item_ids: str, **kwargs) -> None:
        """Require a JSON array of explicit IDs; preserve their input order."""
        super().__init__(*args, **kwargs)
        try:
            values = json.loads(item_ids)
        except (TypeError, ValueError) as exc:
            raise ValueError("item_ids must be a nonempty JSON array of IDs") from exc
        if (
            not isinstance(values, list)
            or not values
            or any(
                not isinstance(value, str) or not value or value != value.strip()
                for value in values
            )
        ):
            raise ValueError("item_ids must be a nonempty JSON array of IDs")
        self.item_ids = tuple(dict.fromkeys(values))

    async def start(self) -> AsyncIterator[Any]:
        """Schedule bounded uncached downloads only for requested items."""
        limit = self._max_raw_content_bytes()
        for item_id in self.item_ids:
            yield self.content_request(
                item_id,
                callback=self.parse_content,
                errback=self.content_errback,
                operation="onedrive-content",
                cb_kwargs={"item_id": item_id, "purpose": "onedrive-content"},
                download_maxsize=limit or None,
            )

    def parse_content(
        self, response: Response, *, item_id: str, purpose: str
    ) -> Iterator[Any]:
        """Sanitize evidence first, then emit digest and size without bytes."""
        evidence = self._raw_http_evidence_item(response, purpose)
        self._redact_download(evidence, item_id)
        yield evidence
        if response.status != 200 or {"partial", "dataloss"}.intersection(
            response.flags
        ):
            raise ValueError("OneDrive content requires a complete HTTP 200 response")
        yield OneDriveContentItem(
            item_id=item_id,
            content_sha256=sha256(response.body).hexdigest(),
            content_bytes=len(response.body),
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )
        self.crawler.stats.inc_value("msgloom/crawl/onedrive/content/item_count")

    def content_errback(self, failure: Failure) -> Iterator[Any]:
        """Retain failure evidence without transport URLs or exception text."""
        request = self._failure_request(failure)
        purpose = request.cb_kwargs["purpose"]
        item_id = request.cb_kwargs["item_id"]
        error_type = failure.type.__name__ if failure.type else "UnknownError"
        # Handler exceptions can include the preauthenticated URL (notably
        # native download_maxsize errors). Never retain arbitrary error text.
        message = "OneDrive content request failed"
        if isinstance(failure.value, HttpError):
            evidence = self._raw_http_evidence_item(
                failure.value.response,
                purpose,
                error_type=error_type,
                error_message=message,
            )
        else:
            evidence = self._raw_http_failure_item(
                request, purpose, error_type=error_type, error_message=message
            )
        self._redact_download(evidence, item_id)
        self.mark_run_failed("request_failure:onedrive-content")
        self.crawler.stats.inc_value("msgloom/crawl/onedrive/content/failure_count")
        self.crawler.stats.inc_value("msgloom/crawl/failure_count")
        self.logger.error(
            "OneDrive content acquisition failed: error_type=%s status=%s",
            error_type,
            evidence.response_status,
        )
        yield evidence
        yield AcquisitionFailureItem(
            url=evidence.request_url,
            purpose=purpose,
            error_type=error_type,
            error_message=message,
            observed_at=evidence.observed_at,
            context={"item_id": item_id},
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )

    def _redact_download(self, evidence: RawHttpEvidenceItem, item_id: str) -> None:
        """Replace transport locations while keeping exact body/status/hash."""
        source_url = f"{self.graph_root}{self.content_path(item_id)}"
        evidence.request_url = source_url
        if evidence.response_url is not None:
            evidence.response_url = source_url
        evidence.request_headers = self._entity_headers(
            evidence.request_headers, allowed=frozenset({"accept", "range"})
        )
        evidence.response_headers = self._entity_headers(evidence.response_headers)
        evidence.response_flags.append("preauthenticated_download_url_redacted")

    @staticmethod
    def _entity_headers(
        headers: dict[str, list[str]], *, allowed: frozenset[str] = _ENTITY_HEADERS
    ) -> dict[str, list[str]]:
        """Keep only known entity headers without embedded absolute URLs."""
        return {
            name: values
            for name, values in headers.items()
            if name.lower() in allowed and not any("://" in value for value in values)
        }
