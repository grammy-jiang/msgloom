"""Persist Outlook semantic items in the shared SQLAlchemy catalog."""

from __future__ import annotations

import asyncio
import logging

from scrapy.exceptions import NotConfigured

from message_ingest.checkpoints import OutlookDeltaCheckpointStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items import (
    OutlookAttachmentItem,
    OutlookDeltaCheckpointCandidateItem,
    OutlookMailDetailItem,
    OutlookMailFolderItem,
    OutlookMailItem,
    OutlookMailRemovalItem,
    OutlookMessageSurfaceItem,
)
from message_ingest.profiles import FULL_V1

logger = logging.getLogger(__name__)


class CatalogPipeline:
    """
    Persist Outlook Mail semantic items after evidence linking.

    ``EvidenceLinkPipeline`` must run earlier in ``ITEM_PIPELINES`` and owns
    canonical evidence validation. All SQL writes complete before
    :meth:`process_item` returns. The shared lock serializes writes from
    different response callbacks; pipeline priority alone does not.
    """

    def __init__(
        self,
        *,
        service: CatalogService,
        source_id: str,
        stats=None,
    ) -> None:
        """
        Borrow shared resources and scope checkpoint candidates to the selected
        source.
        """
        self.service = service
        self.catalog = service.catalog
        self.source_id = source_id
        self.stats = stats
        self._write_lock = service.write_lock
        self.checkpoints = OutlookDeltaCheckpointStore(self.catalog, source_id)

    @classmethod
    def from_crawler(cls, crawler):
        """
        Bind persistence to final crawler settings and the crawler-owned
        service.
        """
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("SQLAlchemy catalog pipeline disabled")
        return cls(
            service=CatalogService.from_crawler(crawler),
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            stats=crawler.stats,
        )

    def close_spider(self) -> None:
        """Close the crawler-shared catalog before terminal lifecycle signals."""
        self.service.close()

    async def process_item(self, item):
        """Await one Outlook Mail domain transaction for supported items."""
        supported = (
            OutlookMailItem,
            OutlookMailDetailItem,
            OutlookAttachmentItem,
            OutlookMailFolderItem,
            OutlookMailRemovalItem,
            OutlookMessageSurfaceItem,
            OutlookDeltaCheckpointCandidateItem,
        )
        if not isinstance(item, supported):
            return item

        async with self._write_lock:
            stat_keys = await asyncio.to_thread(self._process_item_sync, item)
        for stat_key in stat_keys:
            self._inc(stat_key)
        logger.debug(
            "Semantic item persisted to catalog: item_type=%s evidence_id=%s",
            type(item).__name__,
            getattr(item, "evidence_id", None),
        )
        return item

    def _process_item_sync(self, item) -> tuple[str, ...]:
        """
        Dispatch a semantic item inside the write lock and return only its
        successful stat keys.
        """
        if isinstance(item, (OutlookMailItem, OutlookMailDetailItem)):
            return self._record_message(item)
        if isinstance(item, OutlookAttachmentItem):
            self.catalog.upsert_attachment(
                source_id=self.source_id,
                message_id=item.message_id,
                attachment=item.raw,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            return ("msgloom/catalog/attachment_item_processed_count",)
        if isinstance(item, OutlookMailFolderItem):
            self.catalog.upsert_folder(
                source_id=self.source_id,
                folder=item.raw,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            return ("msgloom/catalog/folder_item_processed_count",)
        if isinstance(item, OutlookMailRemovalItem):
            created = self.catalog.record_folder_removal(
                source_id=self.source_id,
                run_id=item.run_id,
                message_id=item.message_id,
                folder_id=item.folder_id,
                removed_reason=item.removed_reason,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            return self._observation_stats("message_folder_removal", created)
        if isinstance(item, OutlookMessageSurfaceItem):
            self.catalog.set_message_surface(
                source_id=self.source_id,
                message_id=item.message_id,
                surface=item.surface,
                status=item.status,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
                profile_version=item.profile_version,
            )
            surface_kind = item.surface.split(":", maxsplit=1)[0]
            return (
                (
                    "msgloom/catalog/surface_item_processed_count/"
                    f"{surface_kind}/{item.status}"
                ),
            )
        if isinstance(item, OutlookDeltaCheckpointCandidateItem):
            self.checkpoints.write_candidate(
                run_id=item.run_id,
                folder_id=item.folder_id,
                delta_link=item.delta_link,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            return ("msgloom/catalog/delta_checkpoint_candidate_processed_count",)
        return ()

    def _record_message(
        self, item: OutlookMailItem | OutlookMailDetailItem
    ) -> tuple[str, ...]:
        """
        Share persistence while preserving discovery/delta/detail kinds,
        surfaces, and stats.
        """
        if isinstance(item, OutlookMailItem):
            kind, surface, profile, stat_prefix = (
                item.observation_kind,
                "discovery",
                None,
                "message",
            )
        else:
            kind, surface, profile, stat_prefix = (
                "detail",
                "detail",
                FULL_V1,
                "message_detail",
            )
        created = self.catalog.record_message(
            source_id=self.source_id,
            run_id=item.run_id,
            message=item.raw,
            kind=kind,
            evidence_id=item.evidence_id,
            observed_at=item.observed_at,
        )
        self.catalog.set_message_surface(
            source_id=self.source_id,
            message_id=item.message_id,
            surface=surface,
            status="acquired",
            evidence_id=item.evidence_id,
            observed_at=item.observed_at,
            profile_version=profile,
        )
        return self._observation_stats(stat_prefix, created)

    @staticmethod
    def _observation_stats(prefix: str, created: bool) -> tuple[str, str]:
        """
        Count every processed item while distinguishing new observations from
        replay.
        """
        outcome = "created" if created else "replay"
        return (
            f"msgloom/catalog/{prefix}_item_processed_count",
            f"msgloom/catalog/{prefix}_observation_{outcome}_count",
        )

    def _inc(self, key: str, count: int = 1) -> None:
        """Keep instrumentation optional for direct pipeline use."""
        if self.stats is not None:
            self.stats.inc_value(key, count=count)
