"""Thin Teams item dispatch with cancellation-safe serialized catalog writes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from scrapy.exceptions import NotConfigured

from message_ingest.acquisition.handoff import (
    AcquisitionFactKind,
    AcquisitionStream,
    FactSpec,
    SourceVersionLocator,
    StorageRelation,
    canonical_json,
    source_state_key,
)
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.teams import (
    TeamsContentStore,
    TeamsCoverageStore,
    TeamsMessageStore,
    TeamsTopologyStore,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.acquisition import RawHttpEvidenceItem
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
_INITIAL_INVENTORIES = {
    "microsoft_teams_chat_discover": {
        "teams-chat-list": AcquisitionStream.TEAMS_CHAT,
    },
    "microsoft_teams_channel_discover": {
        "teams-associated-teams": AcquisitionStream.TEAMS_CHANNEL,
        "teams-joined-teams": AcquisitionStream.TEAMS_CHANNEL,
    },
}


class TeamsPipeline:
    """
    Dispatch pre-parsed Teams items to dedicated stores under one shared lock.

    A cancelled coroutine cannot stop an asyncio worker thread. This pipeline
    uses :meth:`CatalogService.write` to drain a cancelled write under the
    shared lock, then restore and propagate cancellation. A concurrent write
    failure remains chained to cancellation. close_spider acquires the lock so
    the catalog cannot close while this pipeline still has an active thread write.
    """

    def __init__(
        self,
        *,
        service: CatalogService,
        source_id: str,
        spider_name: str | None = None,
        stats=None,
    ) -> None:
        self.service = service
        self.catalog = service.catalog
        self.stats = stats
        self.source_id = source_id
        self.spider_name = spider_name
        self.topology_store = TeamsTopologyStore(
            self.catalog,
            source_id=source_id,
            spider_name=spider_name,
        )
        self.message_store = TeamsMessageStore(
            self.catalog, source_id=source_id, spider_name=spider_name
        )
        self.content_store = TeamsContentStore(
            self.catalog, source_id=source_id, spider_name=spider_name
        )
        self.coverage_store = TeamsCoverageStore(
            self.catalog, source_id=source_id, spider_name=spider_name
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
            spider_name=crawler.spidercls.name,
            stats=crawler.stats,
        )

    async def process_item(self, item: Any) -> Any:
        """Persist supported Teams semantic items and pass unrelated items through."""
        operation: Callable[..., str]
        kwargs: dict[str, str] = {}
        kind: str

        if isinstance(item, RawHttpEvidenceItem):
            expected = _INITIAL_INVENTORIES.get(self.spider_name or "", {})
            if (
                item.purpose in expected
                and item.response_status == 200
                and not item.error_type
            ):
                if not item.run_id:
                    raise ValueError("Teams inventory completion lacks current run")
                await self.service.write(self._record_initial_inventory, item)
            return item

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

        outcome = await self.service.write(operation, item, **kwargs)
        self._record_stats(kind, outcome)
        return item

    def _record_initial_inventory(self, item: RawHttpEvidenceItem) -> None:
        """Bind one successfully processed initial inventory to its logical run.

        Raw capture may be canonicalized to a past cache result. This fact is
        current-run completion proof, never published downstream as source work.
        The existing serial pipeline guarantees raw bytes already committed.
        """
        if self.spider_name not in _INITIAL_INVENTORIES or not item.run_id:
            raise ValueError("Teams inventory proof requires a discovery run")
        stream = _INITIAL_INVENTORIES[self.spider_name][item.purpose]
        with self.catalog.writer_session() as writer:
            evidence = writer.get(RawHttpEvidence, item.evidence_id)
            if (
                evidence is None
                or evidence.source_id != self.source_id
                or evidence.response_status != 200
                or evidence.error_type is not None
                or evidence.purpose != item.purpose
                or evidence.observed_at != item.observed_at
            ):
                raise ValueError("Teams inventory completion lacks canonical evidence")
            identity = canonical_json([item.run_id, item.purpose])
            fact = FactSpec(
                source_id=self.source_id,
                stream=stream,
                run_id=item.run_id,
                spider_name=self.spider_name,
                fact_kind=AcquisitionFactKind.CONTROL_CONTEXT,
                resource_kind="teams_inventory_completion",
                resource_identity=identity,
                scope_kind="teams_initial_inventory",
                scope_identity=item.purpose,
                provider_observed_at=item.observed_at,
                evidence_id=item.evidence_id,
                source_state_key=source_state_key([item.purpose, item.evidence_id]),
                source_version_locator=SourceVersionLocator(
                    kind="evidence",
                    evidence_id=item.evidence_id,
                    resource_identity=identity,
                ),
                storage_relation=StorageRelation.ADVANCED,
            )
            AcquisitionHandoffStore(self.catalog).stage_state_fact_in_session(
                writer, fact
            )

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
