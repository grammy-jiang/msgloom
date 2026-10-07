"""Canonicalize and validate raw-evidence references before domain storage."""

from __future__ import annotations

import asyncio

from scrapy.exceptions import NotConfigured

from message_ingest.acquisition.contracts import EvidenceLinkedItem
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem


class EvidenceLinkPipeline:
    """
    Resolve provider-independent evidence aliases before resource pipelines.

    Raw evidence is persisted by the earlier ``RawEvidencePipeline``. Any later
    item implementing :class:`EvidenceLinkedItem` is rewritten to the canonical
    evidence ID and original observation time, then validated against committed
    raw evidence. Resource pipelines can therefore focus only on domain writes.
    """

    def __init__(self, service: CatalogService) -> None:
        """Borrow the crawler-owned catalog and evidence alias map."""
        self.service = service
        self.catalog = service.catalog

    @classmethod
    def from_crawler(cls, crawler):
        """Enable evidence linking only with the shared SQL catalog."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Evidence linking requires the SQLAlchemy catalog")
        return cls(CatalogService.from_crawler(crawler))

    async def process_item(self, item):
        """
        Validate and canonicalize one evidence-linked item in place.

        ``None`` means the resource item has no evidence reference and requires
        no lookup. An alias miss preserves the supplied ID and timestamp. A
        non-null canonical ID is validated before the item is mutated, so a
        failed lookup leaves the caller's item unchanged.
        """
        if isinstance(item, RawHttpEvidenceItem):
            return item
        if not isinstance(item, EvidenceLinkedItem):
            return item

        canonical_id, observed_at = self.service.resolve_evidence(
            item.evidence_id,
            item.observed_at,
        )
        if canonical_id is not None:
            exists = await asyncio.to_thread(
                self.catalog.evidence.contains,
                canonical_id,
            )
            if not exists:
                raise RuntimeError(
                    "Acquisition item references raw HTTP evidence that has not "
                    "been persisted by RawEvidencePipeline"
                )

        item.evidence_id = canonical_id
        item.observed_at = observed_at
        return item
