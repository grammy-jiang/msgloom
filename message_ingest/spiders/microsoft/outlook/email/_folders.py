"""Abstract folder inventory and reconciliation for Outlook delta sync."""

from __future__ import annotations

from abc import abstractmethod
from urllib.parse import quote, urlencode

import scrapy
from scrapy.http import TextResponse

from message_ingest.items import OutlookMailFolderItem

from ._base import OutlookMailSpider


class OutlookFolderTraversal(OutlookMailSpider):
    """
    Folder inventory and reconciliation callbacks for
    :class:`~message_ingest.spiders.microsoft.outlook.email.delta.OutlookDeltaSpider`.

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
        payload = response.json()
        folders = payload.get("value", [])
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
            yield OutlookMailFolderItem(
                folder_id=folder_id,
                display_name=folder.get("displayName"),
                parent_folder_id=folder.get("parentFolderId"),
                child_folder_count=folder.get("childFolderCount"),
                total_item_count=folder.get("totalItemCount"),
                unread_item_count=folder.get("unreadItemCount"),
                is_hidden=folder.get("isHidden"),
                raw=folder,
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
                    f"{self.graph_root}/me/mailFolders/"
                    f"{quote(folder_id, safe='')}/childFolders?"
                    + urlencode(
                        {"includeHiddenFolders": "true", "$top": self.page_size}
                    ),
                    parent_folder_id=folder_id,
                    page_number=1,
                    purpose="folder-child-list",
                )
            yield self._message_delta_start_request(folder_id)

        if next_link := payload.get("@odata.nextLink"):
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

        if (reconciliation := self._finish_folder_inventory_response()) is not None:
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
        payload = response.json()
        values = payload.get("value", [])
        self.crawler.stats.inc_value("msgloom/crawl/reconcile/page_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/reconcile/message_count", count=len(values)
        )

        for message in values:
            message_id = message.get("id")
            if not isinstance(message_id, str):
                continue
            if message.get("parentFolderId") in self._seen_folder_ids:
                continue
            if message_id in self._reconcile_orphan_ids:
                continue
            self._reconcile_orphan_ids.add(message_id)
            self.crawler.stats.inc_value("msgloom/crawl/reconcile/orphan_count")
            yield self._reconciliation_message_request(message_id)

        if next_link := payload.get("@odata.nextLink"):
            yield self._global_reconciliation_request(
                next_link,
                verbatim_url=True,
            )
            return

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
            response.json(),
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
            query = urlencode(
                {
                    "$select": "id,parentFolderId,lastModifiedDateTime",
                    "$top": 1000,
                }
            )
            url = f"{self.graph_root}/me/messages?{query}"
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
        encoded_id = quote(message_id, safe="")
        query = urlencode({"$select": ",".join(self.discovery_fields)})
        return self._request(
            f"{self.graph_root}/me/messages/{encoded_id}?{query}",
            callback=self.parse_reconciliation_message,
            purpose="message-reconcile",
            cb_kwargs={"message_id": message_id},
            dont_cache=True,
        )
