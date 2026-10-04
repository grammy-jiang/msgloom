"""Thin Teams item dispatch with cancellation-safe serialized catalog writes."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from scrapy.exceptions import NotConfigured

from message_ingest.catalog.stores.microsoft.teams import (
    TeamsContentStore,
    TeamsCoverageStore,
    TeamsMessageStore,
    TeamsTopologyStore,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.teams.content import (
    TeamsHostedContentBytesItem,
    TeamsHostedContentFailureItem,
    TeamsHostedContentItem,
    TeamsReferenceResolutionItem,
)
from message_ingest.items.microsoft.teams.coverage import TeamsCoverageItem
from message_ingest.items.microsoft.teams.message import (
    TeamsMessageDeletionItem,
    TeamsMessageItem,
    TeamsMessageTrigger,
)
from message_ingest.items.microsoft.teams.topology import (
    TeamsChannelItem,
    TeamsChannelMembershipItem,
    TeamsChatItem,
    TeamsChatMemberItem,
    TeamsChatPinItem,
    TeamsPinStateItem,
    TeamsSharedWithTeamItem,
    TeamsTeamItem,
    TeamsTeamMembershipItem,
)

_TOPOLOGY_TYPES = (
    TeamsChatItem,
    TeamsChatMemberItem,
    TeamsChatPinItem,
    TeamsTeamItem,
    TeamsChannelItem,
    TeamsSharedWithTeamItem,
    TeamsTeamMembershipItem,
    TeamsChannelMembershipItem,
    TeamsPinStateItem,
)
_STAT_KINDS = {
    "coverage",
    "deletion",
    "hosted_bytes",
    "hosted_failure",
    "hosted_metadata",
    "message",
    "reference",
    "topology",
}
_STAT_OUTCOMES = {"advanced", "created", "replay", "stale", "tie"}


class TeamsPipeline:
    """
    Dispatch pre-parsed Teams items to dedicated stores under one shared lock.

    A cancelled coroutine cannot stop an asyncio worker thread. This pipeline
    temporarily consumes task cancellation while a write is active, drains the
    worker under the shared lock, then restores and raises cancellation. If the
    drained write also fails, cancellation remains the externally visible
    result and the write failure is chained as its cause. Repeated cancellation
    is restored after the drain. close_spider acquires the same lock, so the
    catalog cannot close while this pipeline still has an active thread write.
    """

    def __init__(
        self,
        *,
        service: CatalogService,
        source_id: str,
        stats=None,
    ) -> None:
        self.service = service
        self.catalog = service.catalog
        self.stats = stats
        self.topology_store = TeamsTopologyStore(
            self.catalog,
            source_id=source_id,
        )
        self.message_store = TeamsMessageStore(
            self.catalog,
            source_id=source_id,
        )
        self.content_store = TeamsContentStore(
            self.catalog,
            source_id=source_id,
        )
        self.coverage_store = TeamsCoverageStore(
            self.catalog,
            source_id=source_id,
        )

    @classmethod
    def from_crawler(cls, crawler):
        """Enable Teams persistence only with one configured shared catalog."""
        if not crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            raise NotConfigured("Teams persistence requires the SQL catalog")
        source_id = crawler.settings.get("MSGLOOM_SOURCE_ID")
        if not isinstance(source_id, str) or not source_id:
            raise NotConfigured("MSGLOOM_SOURCE_ID is required for Teams")
        return cls(
            service=CatalogService.from_crawler(crawler),
            source_id=source_id,
            stats=crawler.stats,
        )

    async def process_item(self, item: Any) -> Any:
        """Persist supported Teams semantic items and pass unrelated items through."""
        operation: Callable[..., str]
        kwargs: dict[str, str] = {}
        kind: str

        if isinstance(item, TeamsMessageItem):
            operation = self.message_store.persist_message
            kind = "message"
        elif isinstance(item, TeamsMessageDeletionItem):
            operation = self.message_store.persist_deletion
            kwargs = self._deletion_aliases(item)
            kind = "deletion"
        elif isinstance(item, TeamsReferenceResolutionItem):
            operation = self.content_store.persist_reference
            kwargs = self._trigger_aliases(item.trigger)
            kind = "reference"
        elif isinstance(item, TeamsHostedContentItem):
            operation = self.content_store.persist_hosted_metadata
            kwargs = self._trigger_aliases(item.trigger)
            kind = "hosted_metadata"
        elif isinstance(item, TeamsHostedContentBytesItem):
            operation = self.content_store.persist_hosted_bytes
            kwargs = self._trigger_aliases(item.trigger)
            kind = "hosted_bytes"
        elif isinstance(item, TeamsHostedContentFailureItem):
            operation = self.content_store.persist_hosted_failure
            kwargs = self._trigger_aliases(item.trigger)
            kind = "hosted_failure"
        elif isinstance(item, TeamsCoverageItem):
            operation = self.coverage_store.persist
            kind = "coverage"
        elif isinstance(item, _TOPOLOGY_TYPES):
            operation = self.topology_store.persist
            kind = "topology"
        else:
            return item

        outcome = await self._write(operation, item, **kwargs)
        self._record_stats(kind, outcome)
        return item

    async def _write(
        self,
        operation: Callable[..., str],
        item: Any,
        **kwargs: str,
    ) -> str:
        """Hold the shared lock until the worker thread has really completed."""
        await self.service.write_lock.acquire()
        worker = asyncio.create_task(asyncio.to_thread(operation, item, **kwargs))
        cancellation: asyncio.CancelledError | None = None
        consumed_cancellations = 0
        current = asyncio.current_task()
        try:
            while True:
                try:
                    outcome = await asyncio.shield(worker)
                    break
                except asyncio.CancelledError as exc:
                    if current is None or current.cancelling() == 0:
                        raise
                    if cancellation is None:
                        cancellation = exc
                    pending = current.cancelling()
                    for _unused in range(pending):
                        current.uncancel()
                        consumed_cancellations += 1
                except BaseException as write_error:
                    if cancellation is None:
                        raise
                    self._restore_cancellation(current, consumed_cancellations)
                    raise cancellation from write_error

            if cancellation is not None:
                self._restore_cancellation(current, consumed_cancellations)
                raise cancellation
            return outcome
        finally:
            self.service.write_lock.release()

    @staticmethod
    def _restore_cancellation(
        current: asyncio.Task[Any] | None,
        count: int,
    ) -> None:
        """Restore every consumed cancellation request after worker drain."""
        if current is None:
            return
        for _unused in range(count):
            current.cancel()

    def _trigger_aliases(self, trigger: TeamsMessageTrigger) -> dict[str, str]:
        """Resolve a follow-up trigger through the shared canonical alias map."""
        evidence_id, observed_at = self.service.resolve_evidence(
            trigger.evidence_id,
            trigger.observed_at,
        )
        if evidence_id is None:
            raise ValueError("Teams follow-up trigger requires canonical evidence")
        return {
            "trigger_evidence_id": evidence_id,
            "trigger_observed_at": observed_at,
        }

    def _deletion_aliases(
        self,
        item: TeamsMessageDeletionItem,
    ) -> dict[str, str]:
        """Resolve optional failed-readback evidence nested in deletion facts."""
        if item.readback_evidence_id is None:
            return {}
        if item.readback_observed_at is None:
            raise ValueError("Teams deletion readback observation time is missing")
        evidence_id, observed_at = self.service.resolve_evidence(
            item.readback_evidence_id,
            item.readback_observed_at,
        )
        if evidence_id is None:
            raise ValueError("Teams deletion readback requires canonical evidence")
        return {
            "readback_evidence_id": evidence_id,
            "readback_observed_at": observed_at,
        }

    def _record_stats(self, kind: str, outcome: str) -> None:
        """Publish only fixed allowlisted stat-key dimensions."""
        if kind not in _STAT_KINDS or outcome not in _STAT_OUTCOMES:
            raise RuntimeError("Unexpected Teams persistence stat dimension")
        if self.stats is None:
            return
        prefix = f"msgloom/catalog/teams/{kind}"
        self.stats.inc_value(f"{prefix}_processed_count")
        self.stats.inc_value(f"{prefix}_{outcome}_count")

    async def close_spider(self, _spider=None) -> None:
        """Close only after any active thread write has drained under the lock."""
        async with self.service.write_lock:
            self.service.close()


__all__ = ["TeamsPipeline"]
