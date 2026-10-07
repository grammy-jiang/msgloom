"""Persist Outlook Mail semantic items through the domain catalog store."""

from __future__ import annotations

import asyncio
import logging

from scrapy.exceptions import NotConfigured

from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.outlook.email import (
    OutlookAttachmentItem,
    OutlookDeltaCheckpointCandidateItem,
    OutlookFolderDeltaCheckpointCandidateItem,
    OutlookFolderSnapshotCandidateItem,
    OutlookMailDetailItem,
    OutlookMailFolderItem,
    OutlookMailFolderRemovalItem,
    OutlookMailInventoryPageItem,
    OutlookMailItem,
    OutlookMailRemovalItem,
    OutlookMessagePresenceCandidateItem,
    OutlookMessagePresenceSightingItem,
    OutlookMessageSurfaceItem,
)
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
    OutlookFolderDeltaCheckpointStore,
)

logger = logging.getLogger(__name__)


class OutlookMailPipeline:
    """Route Outlook Mail items to durable stores after evidence linking."""

    def __init__(
        self,
        *,
        service: CatalogService,
        source_id: str,
        stats=None,
        spider_name: str = "outlook_mail",
    ) -> None:
        self.service = service
        self.catalog = service.catalog
        self.store = OutlookMailStore(
            self.catalog,
            source_id=source_id,
            spider_name=spider_name,
        )
        self.stats = stats
        self._write_lock = service.write_lock
        self.checkpoints = OutlookDeltaCheckpointStore(self.catalog, source_id)
        self.folder_checkpoints = OutlookFolderDeltaCheckpointStore(
            self.catalog, source_id
        )

    @classmethod
    def from_crawler(cls, crawler):
        """Bind persistence to final crawler settings and shared resources."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("SQLAlchemy catalog pipeline disabled")
        return cls(
            service=CatalogService.from_crawler(crawler),
            source_id=crawler.settings["MSGLOOM_SOURCE_ID"],
            stats=crawler.stats,
            spider_name=crawler.spidercls.name or "outlook_mail",
        )

    def close_spider(self) -> None:
        """Close the shared catalog before terminal lifecycle signals."""
        self.service.close()

    async def process_item(self, item):
        """
        Await supported Mail writes while retaining accepted worker ownership.

        One worker holds the existing write lock through real completion,
        including repeated caller cancellation. Ordinary worker errors take
        precedence and retain cancellation as their cause. A successful
        cancelled worker may have committed, but publishes no success stats or
        downstream item. Each existing store transaction keeps its own atomic
        boundary; the worker does not combine them into one transaction.
        The awaited completion future retains errors as results until their
        single disposition here, avoiding cancelled-shield exception logging
        even when a caller is still draining the worker.
        """
        supported = (
            OutlookMailItem,
            OutlookMailInventoryPageItem,
            OutlookMailDetailItem,
            OutlookAttachmentItem,
            OutlookMailFolderItem,
            OutlookMailRemovalItem,
            OutlookMessageSurfaceItem,
            OutlookDeltaCheckpointCandidateItem,
            OutlookFolderSnapshotCandidateItem,
            OutlookFolderDeltaCheckpointCandidateItem,
            OutlookMailFolderRemovalItem,
            OutlookMessagePresenceSightingItem,
            OutlookMessagePresenceCandidateItem,
        )
        if not isinstance(item, supported):
            return item

        if (
            isinstance(
                item,
                (
                    OutlookAttachmentItem,
                    OutlookMessageSurfaceItem,
                    OutlookMailInventoryPageItem,
                ),
            )
            and item.parent_evidence_id is not None
        ):
            parent_id, _ = self.service.resolve_evidence(
                item.parent_evidence_id,
                item.observed_at,
            )
            if parent_id is None or not await asyncio.to_thread(
                self.catalog.evidence.contains, parent_id
            ):
                raise ValueError("Mail parent evidence has not been persisted")
            item.parent_evidence_id = parent_id
        async with self._write_lock:
            write = asyncio.create_task(
                asyncio.to_thread(self._process_item_sync, item)
            )
            completion = asyncio.gather(write, return_exceptions=True)
            cancellation: asyncio.CancelledError | None = None
            try:
                while not completion.done():
                    try:
                        await asyncio.shield(completion)
                    except asyncio.CancelledError as error:
                        if cancellation is None:
                            cancellation = error
                stat_keys = completion.result()[0]
                if isinstance(stat_keys, BaseException):
                    raise stat_keys
            except Exception as error:
                if cancellation is not None:
                    raise error from cancellation
                raise
            if cancellation is not None:
                raise cancellation
        for stat_key in stat_keys:
            self._inc(stat_key)
        logger.debug(
            "Semantic item persisted to catalog: item_type=%s evidence_id=%s",
            type(item).__name__,
            getattr(item, "evidence_id", None),
        )
        return item

    def _process_item_sync(self, item) -> tuple[str, ...]:
        if isinstance(item, (OutlookMailItem, OutlookMailDetailItem)):
            return self._record_message(item)
        if isinstance(item, OutlookMailInventoryPageItem):
            self.store.record_inventory_page(item)
            return ("msgloom/catalog/inventory_page_processed_count",)
        if isinstance(item, OutlookAttachmentItem):
            self.store.upsert_attachment(
                run_id=item.run_id,
                message_id=item.message_id,
                attachment=item.raw,
                resource_version=item.resource_version,
                primary_observed_at=item.primary_observed_at,
                selection_id=item.selection_id,
                parent_evidence_id=item.parent_evidence_id,
                capture_id=item.capture_id,
                profile_version=FULL_V1,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            return ("msgloom/catalog/attachment_item_processed_count",)
        if isinstance(item, OutlookMailFolderItem):
            self.store.upsert_folder(
                folder=item.raw,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
                run_id=item.run_id,
            )
            return ("msgloom/catalog/folder_item_processed_count",)
        if isinstance(item, OutlookMailRemovalItem):
            created = self.store.record_folder_removal(
                run_id=item.run_id,
                message_id=item.message_id,
                folder_id=item.folder_id,
                removed_reason=item.removed_reason,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
            )
            return self._observation_stats("message_folder_removal", created)
        if isinstance(item, OutlookMessageSurfaceItem):
            self.store.set_surface(
                run_id=item.run_id,
                message_id=item.message_id,
                surface=item.surface,
                status=item.status,
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
                profile_version=item.profile_version,
                resource_version=item.resource_version,
                primary_observed_at=item.primary_observed_at,
                selection_id=item.selection_id,
                parent_evidence_id=item.parent_evidence_id,
                capture_id=item.capture_id,
            )
            surface_kind = item.surface.split(":", maxsplit=1)[0]
            return (
                (
                    "msgloom/catalog/surface_item_processed_count/"
                    f"{surface_kind}/{item.status}"
                ),
            )
        if isinstance(item, OutlookMailFolderRemovalItem):
            self.store.mark_folder_removed(
                folder_id=item.folder_id,
                run_id=item.run_id,
                observed_at=item.observed_at,
                evidence_id=item.evidence_id,
                reason=item.removed_reason,
            )
            return ("msgloom/catalog/folder_delta_removed_count",)
        if isinstance(item, OutlookFolderDeltaCheckpointCandidateItem):
            self.folder_checkpoints.write_candidate(
                run_id=item.run_id,
                delta_link=item.delta_link,
                observed_at=item.observed_at,
                evidence_id=item.evidence_id,
            )
            return ("msgloom/catalog/folder_delta_candidate_processed_count",)
        if isinstance(item, OutlookFolderSnapshotCandidateItem):
            self.store.write_folder_snapshot_candidate(
                run_id=item.run_id,
                observed_at=item.observed_at,
                evidence_id=item.evidence_id,
            )
            return ("msgloom/catalog/folder_snapshot_candidate_processed_count",)
        if isinstance(item, OutlookMessagePresenceSightingItem):
            self.store.record_message_sighting(
                run_id=item.run_id,
                message_id=item.message_id,
                observed_at=item.observed_at,
                evidence_id=item.evidence_id,
            )
            return ("msgloom/catalog/message_presence_sighting_processed_count",)
        if isinstance(item, OutlookMessagePresenceCandidateItem):
            self.store.write_message_presence_candidate(
                run_id=item.run_id,
                observed_at=item.observed_at,
                evidence_id=item.evidence_id,
            )
            return ("msgloom/catalog/message_presence_candidate_processed_count",)
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
        self,
        item: OutlookMailItem | OutlookMailDetailItem,
    ) -> tuple[str, ...]:
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
        outcome = self.store.record_message(
            run_id=item.run_id,
            message=item.raw,
            kind=kind,
            selection_id=getattr(item, "selection_id", None),
            evidence_id=item.evidence_id,
            observed_at=item.observed_at,
        )
        if outcome.selection_id is None:
            self.store.set_surface(
                run_id=item.run_id,
                resource_version=outcome.fact.source_state_key,
                primary_observed_at=item.observed_at,
                message_id=item.message_id,
                surface=surface,
                status="acquired",
                evidence_id=item.evidence_id,
                observed_at=item.observed_at,
                profile_version=profile,
            )
        return self._observation_stats(stat_prefix, outcome.observation_created)

    @staticmethod
    def _observation_stats(prefix: str, created: bool) -> tuple[str, str]:
        outcome = "created" if created else "replay"
        return (
            f"msgloom/catalog/{prefix}_item_processed_count",
            f"msgloom/catalog/{prefix}_observation_{outcome}_count",
        )

    def _inc(self, key: str, count: int = 1) -> None:
        if self.stats is not None:
            self.stats.inc_value(key, count=count)


__all__ = ["OutlookMailPipeline"]
