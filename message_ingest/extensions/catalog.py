"""One catalog and write lock shared by the crawler components."""

from __future__ import annotations

import asyncio

from scrapy.exceptions import NotConfigured

from message_ingest.catalog import Catalog

_SERVICE_ATTR = "_msgloom_catalog_service"


class CatalogService:
    """
    Own one engine, write lock, and evidence alias map for a crawler.

    Pipelines and checkpoint consumers borrow this service. Persistence
    pipelines close it idempotently during Scrapy pipeline shutdown, before
    terminal lifecycle observers classify the run.
    """

    def __init__(self, crawler) -> None:
        """
        Create the resources that all enabled persistence components must
        share.
        """
        self.catalog = Catalog(crawler.settings["MSGLOOM_DATABASE_URL"])
        self.write_lock = asyncio.Lock()
        self.evidence_aliases: dict[str, tuple[str, str]] = {}
        self._closed = False

    @classmethod
    def from_crawler(cls, crawler):
        """
        Return the crawler-cached instance, creating shared resources once.
        """
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("SQLAlchemy catalog service disabled")
        if (existing := getattr(crawler, _SERVICE_ATTR, None)) is not None:
            return existing
        service = cls(crawler)
        setattr(crawler, _SERVICE_ATTR, service)
        return service

    def register_evidence_alias(
        self, provisional_id: str, canonical_id: str, observed_at: str
    ) -> None:
        """
        Map this run's provisional evidence ID to the canonical persisted
        capture.
        """
        self.evidence_aliases[provisional_id] = (canonical_id, observed_at)

    def resolve_evidence(
        self, evidence_id: str | None, observed_at: str
    ) -> tuple[str | None, str]:
        """
        Return canonical ID/time together so cache replay cannot advance
        semantic timestamps.
        """
        if evidence_id is None:
            return None, observed_at
        return self.evidence_aliases.get(evidence_id, (evidence_id, observed_at))

    def close(self) -> None:
        """Dispose the shared catalog exactly once after pipeline work."""
        if self._closed:
            return
        self.catalog.close()
        self._closed = True

    def spider_closed(self, *_args, **_kwargs) -> None:
        """Compatibility helper for direct tests; no signal is registered."""
        self.close()
