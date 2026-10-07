"""Recursive personal Contacts snapshot traversal with evidence-first outputs."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any, ClassVar

from scrapy.http import TextResponse
from scrapy.settings import BaseSettings

from message_ingest.catalog.stores.microsoft.contacts import ContactsStore
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items.microsoft.contacts import (
    ContactCollectionCompleteItem,
    ContactFolderItem,
    ContactItem,
)
from message_ingest.spiders.microsoft._graph import MicrosoftGraphSpider
from microsoft_graph.protocol import GraphCollectionPage
from microsoft_graph.spiders.contacts import MicrosoftContactsSpider

from .profile import CONTACT_SELECT_FIELDS, FOLDER_SELECT_FIELDS


class ContactsSnapshotSpider(MicrosoftContactsSpider, MicrosoftGraphSpider):
    """Traverse default contacts plus every custom folder recursively."""

    contact_select_fields = CONTACT_SELECT_FIELDS
    folder_select_fields = FOLDER_SELECT_FIELDS

    failure_context_keys: ClassVar[tuple[str, ...]] = ("folder_id",)
    authoritative_snapshot: ClassVar[bool] = False

    def __init__(self, *args, page_size: str = "100", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )
        self.run_started_at = datetime.now(UTC).isoformat()

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        """Select the Contacts source and lane-specific persistence pipeline."""
        settings.set(
            "MSGLOOM_SOURCE_ID",
            settings.get("MSGLOOM_CONTACTS_SOURCE_ID", "microsoft-contacts-default"),
            priority="spider",
        )
        for key in (
            "MSGLOOM_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_FOLDER_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_CALENDAR_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_ONEDRIVE_DELTA_CHECKPOINT_ENABLED",
            "MSGLOOM_CRAWL_STATUS_ENABLED",
            "MSGLOOM_CONTACTS_DELTA_CHECKPOINT_ENABLED",
        ):
            settings.set(key, False, priority="spider")
        settings.set(
            "MSGLOOM_CONTACTS_SNAPSHOT_PROMOTION_ENABLED",
            cls.authoritative_snapshot,
            priority="spider",
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
        """Reject unvalidated persistent scheduler state before any requests."""
        if crawler.settings.get("JOBDIR"):
            raise ValueError("Contacts snapshots do not support JOBDIR")
        return super().from_crawler(crawler, *args, **kwargs)

    async def start(self) -> AsyncIterator[Any]:
        """Capture promotion ownership, then start the authoritative traversal."""
        if self.authoritative_snapshot and self.crawler.settings.getbool(
            "MSGLOOM_CATALOG_ENABLED"
        ):
            service = CatalogService.from_crawler(self.crawler)
            store = ContactsStore(
                service.catalog,
                source_id=self.crawler.settings["MSGLOOM_SOURCE_ID"],
            )
            await asyncio.to_thread(store.begin_snapshot_run, self.run_id)
        yield self._request(
            self.default_contacts_path(
                page_size=self.page_size, select=self.contact_select_fields
            ),
            callback=self.parse_contacts,
            purpose="contacts-default-page",
            cb_kwargs={"folder_id": None, "is_default_scope": True},
            dont_cache=True,
        )
        yield self._request(
            self.contact_folders_path(
                page_size=self.page_size, select=self.folder_select_fields
            ),
            callback=self.parse_folders,
            purpose="contacts-folder-inventory-page",
            cb_kwargs={"parent_folder_id": None, "root_inventory": True},
            dont_cache=True,
        )

    def parse_folders(
        self,
        response: TextResponse,
        *,
        purpose: str,
        parent_folder_id: str | None,
        root_inventory: bool,
    ) -> Iterator[Any]:
        """Emit folder evidence/state, recurse, and mark only terminal pages complete."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(), context="Contacts folders", validate_links=False
        )
        self.crawler.stats.inc_value("msgloom/crawl/contacts/folder_page_count")
        for raw in page.values:
            item = ContactFolderItem.from_graph(
                raw,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
                run_started_at=self.run_started_at,
            )
            self.crawler.stats.inc_value("msgloom/crawl/contacts/folder_count")
            yield item
            yield self._request(
                self.folder_contacts_path(
                    item.folder_id,
                    page_size=self.page_size,
                    select=self.contact_select_fields,
                ),
                callback=self.parse_contacts,
                purpose="contacts-folder-contacts-page",
                cb_kwargs={"folder_id": item.folder_id, "is_default_scope": False},
                dont_cache=True,
            )
            yield self._request(
                self.child_folders_path(
                    item.folder_id,
                    page_size=self.page_size,
                    select=self.folder_select_fields,
                ),
                callback=self.parse_folders,
                purpose="contacts-child-folders-page",
                cb_kwargs={
                    "parent_folder_id": item.folder_id,
                    "root_inventory": False,
                },
                dont_cache=True,
            )
        if page.next_link:
            yield self._request(
                page.next_link,
                callback=self.parse_folders,
                purpose=purpose,
                cb_kwargs={
                    "parent_folder_id": parent_folder_id,
                    "root_inventory": root_inventory,
                },
                verbatim_url=True,
                dont_cache=True,
            )
            return
        yield ContactCollectionCompleteItem(
            collection_kind="folder_inventory" if root_inventory else "child_folders",
            folder_id=parent_folder_id,
            is_default_scope=False,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
            run_started_at=self.run_started_at,
        )

    def parse_contacts(
        self,
        response: TextResponse,
        *,
        purpose: str,
        folder_id: str | None,
        is_default_scope: bool,
    ) -> Iterator[Any]:
        """Emit complete contact observations and terminal scope completion."""
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(), context="Contacts collection", validate_links=False
        )
        self.crawler.stats.inc_value("msgloom/crawl/contacts/contact_page_count")
        for raw in page.values:
            yield ContactItem.from_graph(
                raw,
                folder_id=folder_id,
                is_default_scope=is_default_scope,
                observation_kind="snapshot",
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
                run_started_at=self.run_started_at,
            )
            self.crawler.stats.inc_value("msgloom/crawl/contacts/contact_count")
        if page.next_link:
            yield self._request(
                page.next_link,
                callback=self.parse_contacts,
                purpose=purpose,
                cb_kwargs={
                    "folder_id": folder_id,
                    "is_default_scope": is_default_scope,
                },
                verbatim_url=True,
                dont_cache=True,
            )
            return
        yield ContactCollectionCompleteItem(
            collection_kind="contacts",
            folder_id=folder_id,
            is_default_scope=is_default_scope,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
            run_id=self.run_id,
            run_started_at=self.run_started_at,
        )


class MicrosoftContactsDiscoverSpider(ContactsSnapshotSpider):
    """Collect Contacts evidence and additive state without absence inference."""

    name = "microsoft_contacts_discover"


class MicrosoftContactsSyncSpider(ContactsSnapshotSpider):
    """Promote authoritative presence only after a complete clean snapshot."""

    name = "microsoft_contacts_sync"
    authoritative_snapshot = True


__all__ = [
    "ContactsSnapshotSpider",
    "MicrosoftContactsDiscoverSpider",
    "MicrosoftContactsSyncSpider",
]
