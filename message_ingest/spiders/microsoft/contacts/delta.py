"""Safe per-folder Contacts delta for a concrete custom-folder identity."""

import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any

from scrapy.http import TextResponse
from scrapy.settings import BaseSettings

from message_ingest.catalog.stores.microsoft.contacts import ContactsStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.contacts import (
    ContactDeltaCheckpointCandidateItem,
    ContactItem,
)
from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from message_ingest.sync.microsoft.contacts import require_custom_folder_scope
from microsoft_graph.protocol import GraphDeltaPage
from microsoft_graph.spiders.contacts import MicrosoftContactsSpider

from .profile import CONTACT_SELECT_FIELDS


class MicrosoftContactsDeltaSpider(MicrosoftContactsSpider, MicrosoftGraphSpider):
    """Track one validated custom folder; default Contacts delta is unsupported."""

    name = "microsoft_contacts_delta"
    contact_select_fields = CONTACT_SELECT_FIELDS

    failure_context_keys = ("folder_id",)

    def __init__(self, *args, folder_id: str, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.folder_id = require_custom_folder_scope(folder_id)
        self._folder_id(self.folder_id)
        self.run_started_at = datetime.now(UTC).isoformat()
        self.base_revision: int | None = None
        self.terminal_delta_seen = False

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Enable only Contacts persistence and the custom-folder delta gate."""
        settings.set(
            "MSGLOOM_SOURCE_ID",
            settings.get("MSGLOOM_CONTACTS_SOURCE_ID", "microsoft-contacts-default"),
            priority="spider",
        )
        settings.set(
            "MSGLOOM_CONTACTS_DELTA_CHECKPOINT_ENABLED", True, priority="spider"
        )
        settings.set(
            "MSGLOOM_CONTACTS_SNAPSHOT_PROMOTION_ENABLED", False, priority="spider"
        )
        settings.set(
            "ITEM_PIPELINES",
            {
                "message_ingest.pipelines.evidence.RawEvidencePipeline": 200,
                "message_ingest.acquisition.evidence_link.EvidenceLinkPipeline": 250,
                "message_ingest.pipelines.microsoft.contacts.ContactsPipeline": 300,
            },
            priority="spider",
        )
        super().update_settings(settings)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Reject JOBDIR until a Contacts delta resume contract is qualified."""
        if crawler.settings.get("JOBDIR"):
            raise ValueError("Contacts delta does not support JOBDIR")
        return super().from_crawler(crawler, *args, **kwargs)

    async def start(self) -> AsyncIterator[Any]:
        """Resume one opaque folder cursor or start that folder's initial delta."""
        checkpoint = None
        if self.crawler.settings.getbool("MSGLOOM_CATALOG_ENABLED"):
            service = CatalogService.from_crawler(self.crawler)
            store = ContactsStore(
                service.catalog, source_id=self.crawler.settings["MSGLOOM_SOURCE_ID"]
            )
            checkpoint = await asyncio.to_thread(
                store.begin_delta_run,
                folder_id=self.folder_id,
                run_id=self.run_id,
            )
        if checkpoint is not None:
            self.base_revision = checkpoint.revision
        yield self._request(
            checkpoint.delta_link
            if checkpoint is not None
            else self.contacts_delta_path(
                self.folder_id, select=self.contact_select_fields
            ),
            callback=self.parse_delta,
            purpose="contacts-delta-page",
            cb_kwargs={"folder_id": self.folder_id},
            verbatim_url=checkpoint is not None,
            dont_cache=True,
        )

    def parse_delta(
        self, response: TextResponse, *, purpose: str, folder_id: str
    ) -> Iterator[Any]:
        """Stage sparse changes/tombstones and preserve opaque continuation bytes."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphDeltaPage.from_payload(
            response.json(),
            context="Contacts custom-folder delta",
            strict=False,
            validate_links=False,
        )
        self.crawler.stats.inc_value("msgloom/crawl/contacts/delta/page_count")
        for raw in page.values:
            yield ContactItem.from_graph(
                raw,
                folder_id=folder_id,
                is_default_scope=False,
                observation_kind="delta",
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
                run_started_at=self.run_started_at,
            )
            self.crawler.stats.inc_value("msgloom/crawl/contacts/delta/item_count")
        page.validate_state()
        if page.next_link:
            yield self._request(
                page.next_link,
                callback=self.parse_delta,
                purpose=purpose,
                cb_kwargs={"folder_id": folder_id},
                verbatim_url=True,
                dont_cache=True,
            )
            return
        if page.delta_link is None:
            raise ValueError("Contacts terminal delta requires a deltaLink")
        self.terminal_delta_seen = True
        yield ContactDeltaCheckpointCandidateItem(
            folder_id=folder_id,
            delta_link=page.delta_link,
            base_revision=self.base_revision,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
        )


__all__ = ["MicrosoftContactsDeltaSpider"]
