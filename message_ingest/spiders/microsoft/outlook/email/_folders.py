"""Abstract folder inventory and reconciliation for Outlook delta sync."""

from __future__ import annotations

from abc import abstractmethod

import scrapy
from scrapy.http import TextResponse

from message_ingest.items.microsoft.outlook.email import (
    OutlookFolderSnapshotCandidateItem,
    OutlookMailFolderItem,
    OutlookMessagePresenceCandidateItem,
    OutlookMessagePresenceSightingItem,
)
from microsoft_graph.protocol import GraphCollectionPage, graph_object

from ._base import OutlookMailCollectionSpider


class OutlookFolderTraversal(OutlookMailCollectionSpider):
    """
    Own folder inventory and reconciliation during Outlook Mail delta sync.

    These stay bound to the spider so Scrapy can serialize their requests. The
    concrete delta spider persists this traversal state.
    """

    page_size: int
    reconcile_global: bool

    def __init__(self, *args, **kwargs) -> None:
        """
        Track outstanding inventory pages separately from folder delta
        completion.
        """
        super().__init__(*args, **kwargs)
        self._seen_folder_ids: set[str] = set()
        self._started_folder_ids: set[str] = set()
        self._reconcile_orphan_ids: set[str] = set()
        self._folder_inventory_pending = 0
        self._folder_inventory_complete = False
        self._folder_inventory_failed = False
        self._reconcile_complete = False

    @abstractmethod
    def _persist_execution_state(self) -> None:
        """
        Mirror the delta execution state into Scrapy
        :class:`~scrapy.extensions.spiderstate.SpiderState`.
        """
        raise NotImplementedError

    @abstractmethod
    def _message_delta_start_request(self, folder_id: str) -> scrapy.Request:
        """Start or resume the delta round for an inventoried folder."""
        raise NotImplementedError

    def parse_folders(
        self,
        response: TextResponse,
        *,
        purpose: str,
        parent_folder_id: str | None,
        page_number: int,
    ):
        """
        Emit folder observations and schedule each distinct folder's traversal
        once.

        Record child/next-page requests before retiring this page from the
        pending count. Only the last successful inventory response may start
        global reconciliation.
        """
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        # Mail inventories retain missing values and falsey-link compatibility.
        # Defer continuation validation until after evidence and observations.
        page = GraphCollectionPage.from_payload(
            response.json(),
            missing_value_empty=True,
            empty_links_absent=True,
            validate_links=False,
        )
        folders = page.values
        self.logger.debug(
            "Processed Outlook folder page: purpose=%s page=%s folders=%s",
            purpose,
            page_number,
            len(folders),
        )
        self.crawler.stats.inc_value("msgloom/crawl/delta/folder_page_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/delta/folder_observation_count", count=len(folders)
        )

        for folder in folders:
            folder_id = folder["id"]
            yield OutlookMailFolderItem.from_graph(
                folder,
                source_response_url=response.url,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
                run_id=self.run_id,
            )

            if folder_id in self._seen_folder_ids:
                self.crawler.stats.inc_value(
                    "msgloom/crawl/delta/folder_duplicate_count"
                )
                continue

            self._seen_folder_ids.add(folder_id)
            self._started_folder_ids.add(folder_id)
            self._persist_execution_state()
            self.crawler.stats.inc_value("msgloom/crawl/delta/folder_count")
            if (folder.get("childFolderCount") or 0) > 0:
                self.crawler.stats.inc_value(
                    "msgloom/crawl/delta/child_folder_traversal_request_count"
                )
                yield self._folder_list_request(
                    self.mail_folders_path(
                        parent_folder_id=folder_id,
                        include_hidden=True,
                        page_size=self.page_size,
                    ),
                    parent_folder_id=folder_id,
                    page_number=1,
                    purpose="folder-child-list",
                )
            yield self._message_delta_start_request(folder_id)

        if next_link := page.next_link:
            self.crawler.stats.inc_value(
                "msgloom/crawl/delta/folder_continuation_count"
            )
            yield self._folder_list_request(
                next_link,
                parent_folder_id=parent_folder_id,
                page_number=page_number + 1,
                purpose=purpose,
                verbatim_url=True,
            )

        was_complete = self._folder_inventory_complete
        reconciliation = self._finish_folder_inventory_response()
        if not was_complete and self._folder_inventory_complete:
            yield OutlookFolderSnapshotCandidateItem(
                run_id=self.run_id,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
            )
        if reconciliation is not None:
            yield reconciliation

    def parse_global_reconciliation(
        self,
        response: TextResponse,
        *,
        purpose: str = "message-reconcile-list",
    ):
        """
        Stream recovery requests for messages outside the inventoried folder
        set.

        Keep only orphan IDs for deduplication; do not accumulate the entire
        mailbox. The final list page completes traversal, but pending recovery
        writes still keep Scrapy busy and any recovery failure invalidates the
        run.
        """
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        page = GraphCollectionPage.from_payload(
            response.json(),
            missing_value_empty=True,
            empty_links_absent=True,
            validate_links=False,
        )
        values = page.values
        self.crawler.stats.inc_value("msgloom/crawl/reconcile/page_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/reconcile/message_count", count=len(values)
        )

        for message in values:
            message_id = message.get("id")
            if not isinstance(message_id, str):
                continue
            yield OutlookMessagePresenceSightingItem(
                run_id=self.run_id,
                message_id=message_id,
                observed_at=evidence.observed_at,
                evidence_id=evidence.evidence_id,
            )
            if message.get("parentFolderId") in self._seen_folder_ids:
                continue
            if message_id in self._reconcile_orphan_ids:
                continue
            self._reconcile_orphan_ids.add(message_id)
            self.crawler.stats.inc_value("msgloom/crawl/reconcile/orphan_count")
            yield self._reconciliation_message_request(message_id)

        if next_link := page.next_link:
            yield self._global_reconciliation_request(
                next_link,
                verbatim_url=True,
            )
            return

        yield OutlookMessagePresenceCandidateItem(
            run_id=self.run_id,
            observed_at=evidence.observed_at,
            evidence_id=evidence.evidence_id,
        )
        self._reconcile_complete = True
        self._persist_execution_state()
        self.crawler.stats.set_value("msgloom/crawl/reconcile/completed", True)
        self.logger.info(
            "Outlook reconciliation complete: messages=%s orphans=%s",
            self.crawler.stats.get_value("msgloom/crawl/reconcile/message_count", 0),
            self.crawler.stats.get_value("msgloom/crawl/reconcile/orphan_count", 0),
        )

    def parse_reconciliation_message(
        self,
        response: TextResponse,
        *,
        purpose: str,
        message_id: str,
    ):
        """Emit a recovered message with its acquisition evidence."""
        self.logger.debug(
            "Recovered Outlook reconciliation message: message_id=%s", message_id
        )
        evidence = self._raw_http_evidence_item(response, purpose)
        yield evidence
        self.crawler.stats.inc_value("msgloom/crawl/reconcile/message_recovered_count")
        yield self._message_item(
            graph_object(response.json(), context="Outlook reconciliation message"),
            response.url,
            evidence.observed_at,
            observation_kind="reconcile",
            evidence_id=evidence.evidence_id,
        )

    def _folder_list_request(
        self,
        url: str,
        *,
        parent_folder_id: str | None,
        page_number: int,
        purpose: str,
        verbatim_url: bool = False,
    ) -> scrapy.Request:
        """
        Count pending work at request creation; hidden folders remain part of
        inventory.
        """
        self._folder_inventory_pending += 1
        self._persist_execution_state()
        return self._request(
            url,
            callback=self.parse_folders,
            purpose=purpose,
            cb_kwargs={
                "parent_folder_id": parent_folder_id,
                "page_number": page_number,
            },
            dont_cache=True,
            verbatim_url=verbatim_url,
            prefer=None,
        )

    def _finish_folder_inventory_response(self) -> scrapy.Request | None:
        """
        Start reconciliation once, only after every inventory page succeeds.
        """
        self._folder_inventory_pending -= 1
        self._persist_execution_state()
        if self._folder_inventory_pending != 0 or self._folder_inventory_complete:
            return None
        if self._folder_inventory_failed:
            return None

        self._folder_inventory_complete = True
        self._persist_execution_state()
        self.crawler.stats.set_value(
            "msgloom/crawl/delta/folder_inventory_completed", True
        )
        self.logger.info(
            "Outlook folder inventory complete: folders=%s reconciliation=%s",
            len(self._seen_folder_ids),
            self.reconcile_global,
        )
        if not self.reconcile_global:
            self._reconcile_complete = True
            self._persist_execution_state()
            self.crawler.stats.set_value("msgloom/crawl/reconcile/completed", True)
            return None
        return self._global_reconciliation_request()

    def _global_reconciliation_request(
        self,
        url: str | None = None,
        *,
        verbatim_url: bool = False,
    ) -> scrapy.Request:
        """
        Scan lightweight mailbox IDs, following provider continuation URLs
        unchanged.
        """
        if url is None:
            path = self.messages_path(
                fields=("id", "parentFolderId", "lastModifiedDateTime"),
                page_size=1000,
            )
            url = f"{self.graph_root}{path}"
        return self._request(
            url,
            callback=self.parse_global_reconciliation,
            purpose="message-reconcile-list",
            cb_kwargs={},
            verbatim_url=verbatim_url,
            dont_cache=True,
        )

    def _reconciliation_message_request(self, message_id: str) -> scrapy.Request:
        """
        Fetch discovery metadata for an orphan message without cache replay.
        """
        return self._request(
            self.message_path(message_id, fields=self.discovery_fields),
            callback=self.parse_reconciliation_message,
            purpose="message-reconcile",
            cb_kwargs={"message_id": message_id},
            dont_cache=True,
        )
