from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlencode
from uuid import uuid4

import scrapy
from twisted.python.failure import Failure

from msgloom.checkpoints import OutlookDeltaCheckpointStore
from msgloom.evidence import META_EVIDENCE_ID, META_PURPOSE, META_RUN_ID
from msgloom.items import (
    AcquisitionFailureItem,
    OutlookAttachmentItem,
    OutlookDeltaCheckpointCandidateItem,
    OutlookMailDetailItem,
    OutlookMailFolderItem,
    OutlookMailItem,
    OutlookMailRemovalItem,
    OutlookMessageSurfaceItem,
)


class OutlookMailSpider(scrapy.Spider):
    name = "outlook_mail"
    allowed_domains = ["graph.microsoft.com"]
    graph_root = "https://graph.microsoft.com/v1.0"

    discovery_fields = (
        "id",
        "subject",
        "from",
        "sender",
        "toRecipients",
        "ccRecipients",
        "bccRecipients",
        "replyTo",
        "receivedDateTime",
        "sentDateTime",
        "createdDateTime",
        "lastModifiedDateTime",
        "importance",
        "isRead",
        "isDraft",
        "hasAttachments",
        "conversationId",
        "conversationIndex",
        "inferenceClassification",
        "flag",
        "categories",
        "bodyPreview",
        "parentFolderId",
        "webLink",
        "internetMessageId",
    )

    full_fields = discovery_fields + (
        "body",
        "changeKey",
        "internetMessageHeaders",
        "isDeliveryReceiptRequested",
        "isReadReceiptRequested",
        "uniqueBody",
    )

    def __init__(
        self,
        folder: str = "",
        page_size: str = "25",
        max_pages: str = "0",
        message_ids: str = "",
        sync_mode: str = "discovery",
        reconcile_global: str = "1",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.folder = folder
        self.page_size = self._bounded_int(
            page_size, name="page_size", minimum=1, maximum=1000
        )
        self.max_pages = self._bounded_int(max_pages, name="max_pages", minimum=0)
        self.message_ids = tuple(
            message_id.strip()
            for message_id in message_ids.split(",")
            if message_id.strip()
        )
        self.sync_mode = sync_mode.strip().lower()
        if self.sync_mode not in {"discovery", "delta"}:
            raise ValueError("sync_mode must be 'discovery' or 'delta'")

        self.run_id = uuid4().hex
        self.reconcile_global = reconcile_global.strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        self._seen_folder_ids: set[str] = set()
        self._reconcile_orphan_ids: set[str] = set()
        self._checkpoint_store: OutlookDeltaCheckpointStore | None = None
        self._delta_links: dict[str, str] = {}
        self._folder_inventory_pending = 0
        self._folder_inventory_complete = False
        self._folder_inventory_failed = False

    async def start(self):
        if self.message_ids:
            self.crawler.stats.set_value("msgloom/crawl/mode", "full")
            self.crawler.stats.set_value(
                "msgloom/crawl/enrichment/target_message_count",
                len(self.message_ids),
            )
            for message_id in self.message_ids:
                for request in self._full_requests(message_id):
                    yield request
            return

        if self.sync_mode == "delta":
            self._delta_links = await asyncio.to_thread(
                self._delta_checkpoint_store().get_delta_links
            )
            self.crawler.stats.set_value(
                "msgloom/crawl/delta/checkpoint_loaded_count", len(self._delta_links)
            )
            self.crawler.stats.set_value("msgloom/crawl/mode", "delta")
            self.crawler.stats.set_value("msgloom/crawl/run_id", self.run_id)
            self.crawler.stats.set_value(
                "msgloom/crawl/reconcile/enabled", self.reconcile_global
            )
            yield self._folder_list_request(
                f"{self.graph_root}/me/mailFolders?"
                + urlencode(
                    {"includeHiddenFolders": "true", "$top": self.page_size}
                ),
                parent_folder_id=None,
                page_number=1,
                purpose="folder-list",
            )
            return

        self.crawler.stats.set_value("msgloom/crawl/mode", "discovery")
        self.crawler.stats.set_value(
            "msgloom/crawl/discovery/scope",
            "folder" if self.folder else "mailbox",
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/discovery/page_size", self.page_size
        )
        self.crawler.stats.set_value(
            "msgloom/crawl/discovery/max_pages", self.max_pages
        )

        query = urlencode(
            {
                "$select": ",".join(self.discovery_fields),
                "$orderby": "receivedDateTime desc",
                "$top": self.page_size,
            }
        )
        if self.folder:
            base_url = (
                f"{self.graph_root}/me/mailFolders/"
                f"{quote(self.folder, safe='')}/messages"
            )
        else:
            base_url = f"{self.graph_root}/me/messages"
        yield self._message_list_request(f"{base_url}?{query}", page_number=1)

    def parse(
        self,
        response: scrapy.http.Response,
        *,
        purpose: str = "message-list",
        page_number: int = 1,
    ):
        """
        Parse one Graph message-list page.

        @url data:application/json,%7B%22value%22%3A%5B%7B%22id%22%3A%22m1%22%2C%22subject%22%3A%22Hello%22%2C%22from%22%3A%7B%22emailAddress%22%3A%7B%22address%22%3A%22sender%40example.com%22%7D%7D%7D%5D%7D
        @returns items 1 1
        @returns requests 0 0
        """
        observed_at = self._now()
        evidence_id = self._evidence_id(response)
        payload = response.json()
        messages = payload.get("value", [])
        self.crawler.stats.inc_value("msgloom/crawl/discovery/page_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/discovery/message_count", count=len(messages)
        )
        for message in messages:
            yield self._message_item(
                message,
                response.url,
                observed_at,
                observation_kind="discovery",
                evidence_id=evidence_id,
            )

        next_link = payload.get("@odata.nextLink")
        if next_link and (self.max_pages == 0 or page_number < self.max_pages):
            self.crawler.stats.inc_value(
                "msgloom/crawl/discovery/continuation_count"
            )
            yield self._message_list_request(
                next_link,
                page_number=page_number + 1,
                verbatim_url=True,
            )
        elif next_link:
            self.crawler.stats.inc_value("msgloom/crawl/discovery/truncated_count")

    def parse_folders(
        self,
        response: scrapy.http.Response,
        *,
        purpose: str,
        parent_folder_id: str | None,
        page_number: int,
    ):
        observed_at = self._now()
        evidence_id = self._evidence_id(response)
        payload = response.json()
        folders = payload.get("value", [])
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
                observed_at=observed_at,
                evidence_id=evidence_id,
                run_id=self.run_id,
            )

            if folder_id in self._seen_folder_ids:
                self.crawler.stats.inc_value(
                    "msgloom/crawl/delta/folder_duplicate_count"
                )
                continue

            self._seen_folder_ids.add(folder_id)
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

        next_link = payload.get("@odata.nextLink")
        if next_link:
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

        reconciliation = self._finish_folder_inventory_response()
        if reconciliation is not None:
            yield reconciliation

    def parse_global_reconciliation(
        self,
        response: scrapy.http.Response,
        *,
        purpose: str = "message-reconcile-list",
    ):
        observed_at = self._now()
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

        next_link = payload.get("@odata.nextLink")
        if next_link:
            yield self._global_reconciliation_request(
                next_link,
                verbatim_url=True,
            )
            return

        self.crawler.stats.set_value("msgloom/crawl/reconcile/completed", True)

    def parse_reconciliation_message(
        self,
        response: scrapy.http.Response,
        *,
        purpose: str,
        message_id: str,
    ):
        observed_at = self._now()
        self.crawler.stats.inc_value(
            "msgloom/crawl/reconcile/message_recovered_count"
        )
        yield self._message_item(
            response.json(),
            response.url,
            observed_at,
            observation_kind="reconcile",
            evidence_id=self._evidence_id(response),
        )

    def parse_message_delta(
        self,
        response: scrapy.http.Response,
        *,
        purpose: str,
        folder_id: str,
        page_number: int,
    ):
        observed_at = self._now()
        evidence_id = self._evidence_id(response)
        payload = response.json()
        values = payload.get("value", [])
        self.crawler.stats.inc_value("msgloom/crawl/delta/message_page_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/delta/message_observation_count", count=len(values)
        )

        for message in values:
            removed = message.get("@removed")
            if isinstance(removed, dict):
                self.crawler.stats.inc_value(
                    "msgloom/crawl/delta/message_removed_count"
                )
                reason = removed.get("reason")
                if reason:
                    self.crawler.stats.inc_value(
                        f"msgloom/crawl/delta/message_removed_reason_count/{reason}"
                    )
                yield OutlookMailRemovalItem(
                    message_id=message["id"],
                    folder_id=folder_id,
                    removed_reason=reason,
                    raw=message,
                    source_response_url=response.url,
                    observed_at=observed_at,
                    evidence_id=evidence_id,
                    run_id=self.run_id,
                )
            else:
                self.crawler.stats.inc_value(
                    "msgloom/crawl/delta/message_upsert_count"
                )
                yield self._message_item(
                    message,
                    response.url,
                    observed_at,
                    observation_kind="delta",
                    evidence_id=evidence_id,
                )

        next_link = payload.get("@odata.nextLink")
        delta_link = payload.get("@odata.deltaLink")
        if next_link:
            self.crawler.stats.inc_value(
                "msgloom/crawl/delta/message_continuation_count"
            )
            yield self._message_delta_request(
                next_link,
                folder_id=folder_id,
                page_number=page_number + 1,
            )
            return

        if delta_link:
            self.crawler.stats.inc_value(
                "msgloom/crawl/delta/folder_completed_count"
            )
            yield OutlookDeltaCheckpointCandidateItem(
                run_id=self.run_id,
                folder_id=folder_id,
                delta_link=delta_link,
                observed_at=observed_at,
                evidence_id=evidence_id,
            )
            return

        self.crawler.stats.inc_value("msgloom/crawl/failure_count")
        self.crawler.stats.inc_value(
            "msgloom/crawl/failure_purpose_count/message-delta"
        )
        self.crawler.stats.inc_value(
            "msgloom/crawl/failure_type_count/DeltaStateMissing"
        )
        yield AcquisitionFailureItem(
            url=response.url,
            purpose="message-delta",
            error_type="DeltaStateMissing",
            error_message=(
                "Microsoft Graph delta response contained neither "
                "@odata.nextLink nor @odata.deltaLink"
            ),
            observed_at=observed_at,
            folder_id=folder_id,
            evidence_id=evidence_id,
            run_id=self.run_id,
        )

    def parse_message_detail(
        self,
        response: scrapy.http.Response,
        *,
        purpose: str,
        message_id: str,
    ):
        observed_at = self._now()
        self.crawler.stats.inc_value(
            "msgloom/crawl/enrichment/message_detail_count"
        )
        yield OutlookMailDetailItem(
            message_id=message_id,
            raw=response.json(),
            source_response_url=response.url,
            observed_at=observed_at,
            evidence_id=self._evidence_id(response),
            run_id=self.run_id,
        )

    def parse_raw_evidence(
        self,
        response: scrapy.http.Response,
        *,
        purpose: str,
        message_id: str,
        attachment_id: str | None = None,
    ):
        observed_at = self._now()
        evidence_id = self._evidence_id(response)
        if purpose == "message-mime":
            self.crawler.stats.inc_value(
                "msgloom/crawl/enrichment/message_mime_count"
            )
            yield OutlookMessageSurfaceItem(
                message_id=message_id,
                surface="mime",
                status="acquired",
                observed_at=observed_at,
                evidence_id=evidence_id,
            )
        elif purpose == "attachment-raw" and attachment_id:
            self.crawler.stats.inc_value(
                "msgloom/crawl/enrichment/attachment_raw_count"
            )
            yield OutlookMessageSurfaceItem(
                message_id=message_id,
                surface=f"attachment_raw:{attachment_id}",
                status="acquired",
                observed_at=observed_at,
                evidence_id=evidence_id,
            )

    def parse_attachments(
        self,
        response: scrapy.http.Response,
        *,
        purpose: str,
        message_id: str,
        page_number: int,
    ):
        observed_at = self._now()
        evidence_id = self._evidence_id(response)
        payload = response.json()
        attachments = payload.get("value", [])
        self.crawler.stats.inc_value(
            "msgloom/crawl/enrichment/attachment_page_count"
        )
        self.crawler.stats.inc_value(
            "msgloom/crawl/enrichment/attachment_count", count=len(attachments)
        )
        for attachment in attachments:
            attachment_id = attachment["id"]
            attachment_type = attachment.get("@odata.type")
            attachment_type_name = self._attachment_type_name(attachment_type)
            self.crawler.stats.inc_value(
                f"msgloom/crawl/enrichment/attachment_type_count/{attachment_type_name}"
            )
            yield OutlookAttachmentItem(
                message_id=message_id,
                attachment_id=attachment_id,
                attachment_type=attachment_type,
                raw=attachment,
                source_response_url=response.url,
                observed_at=observed_at,
                evidence_id=evidence_id,
                run_id=self.run_id,
            )

            if attachment_type in {
                "#microsoft.graph.fileAttachment",
                "microsoft.graph.fileAttachment",
                "#microsoft.graph.itemAttachment",
                "microsoft.graph.itemAttachment",
            }:
                yield self._attachment_raw_request(message_id, attachment_id)

            if attachment_type in {
                "#microsoft.graph.itemAttachment",
                "microsoft.graph.itemAttachment",
            }:
                yield self._item_attachment_detail_request(message_id, attachment_id)

        next_link = payload.get("@odata.nextLink")
        if next_link:
            self.crawler.stats.inc_value(
                "msgloom/crawl/enrichment/attachment_continuation_count"
            )
            yield self._attachments_request(
                message_id,
                url=next_link,
                page_number=page_number + 1,
                verbatim_url=True,
            )
        else:
            yield OutlookMessageSurfaceItem(
                message_id=message_id,
                surface="attachments",
                status="acquired",
                observed_at=observed_at,
                evidence_id=evidence_id,
            )

    def parse_attachment_detail(
        self,
        response: scrapy.http.Response,
        *,
        purpose: str,
        message_id: str,
        attachment_id: str,
    ):
        observed_at = self._now()
        evidence_id = self._evidence_id(response)
        self.crawler.stats.inc_value(
            "msgloom/crawl/enrichment/item_attachment_detail_count"
        )
        payload = response.json()
        yield OutlookAttachmentItem(
            message_id=message_id,
            attachment_id=attachment_id,
            attachment_type=payload.get("@odata.type"),
            raw=payload,
            source_response_url=response.url,
            observed_at=observed_at,
            evidence_id=evidence_id,
            run_id=self.run_id,
        )
        yield OutlookMessageSurfaceItem(
            message_id=message_id,
            surface=f"item_attachment_detail:{attachment_id}",
            status="acquired",
            observed_at=observed_at,
            evidence_id=evidence_id,
        )

    def errback(self, failure: Failure):
        request = failure.request
        callback_data = request.cb_kwargs
        purpose = callback_data.get("purpose", request.meta.get(META_PURPOSE, "unknown"))
        error_type = failure.type.__name__ if failure.type else "UnknownError"

        if purpose in {"folder-list", "folder-child-list"}:
            self._folder_inventory_failed = True
            self._folder_inventory_pending = max(0, self._folder_inventory_pending - 1)
            self.crawler.stats.set_value(
                "msgloom/crawl/delta/folder_inventory_failed", True
            )

        self.crawler.stats.inc_value("msgloom/crawl/failure_count")
        self.crawler.stats.inc_value(
            f"msgloom/crawl/failure_purpose_count/{purpose}"
        )
        self.crawler.stats.inc_value(
            f"msgloom/crawl/failure_type_count/{error_type}"
        )
        yield AcquisitionFailureItem(
            url=request.url,
            purpose=purpose,
            error_type=error_type,
            error_message=failure.getErrorMessage(),
            observed_at=self._now(),
            message_id=callback_data.get("message_id"),
            attachment_id=callback_data.get("attachment_id"),
            folder_id=callback_data.get("folder_id"),
            evidence_id=request.meta.get(META_EVIDENCE_ID),
            run_id=self.run_id,
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
        self._folder_inventory_pending += 1
        return self._request(
            url,
            callback=self.parse_folders,
            purpose=purpose,
            cb_kwargs={
                "purpose": purpose,
                "parent_folder_id": parent_folder_id,
                "page_number": page_number,
            },
            dont_cache=True,
            verbatim_url=verbatim_url,
            prefer=None,
        )

    def _finish_folder_inventory_response(self) -> scrapy.Request | None:
        self._folder_inventory_pending -= 1
        if self._folder_inventory_pending != 0 or self._folder_inventory_complete:
            return None
        if self._folder_inventory_failed:
            return None

        self._folder_inventory_complete = True
        self.crawler.stats.set_value(
            "msgloom/crawl/delta/folder_inventory_completed", True
        )
        if not self.reconcile_global:
            self.crawler.stats.set_value("msgloom/crawl/reconcile/completed", True)
            return None
        return self._global_reconciliation_request()

    def _global_reconciliation_request(
        self,
        url: str | None = None,
        *,
        verbatim_url: bool = False,
    ) -> scrapy.Request:
        purpose = "message-reconcile-list"
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
            purpose=purpose,
            cb_kwargs={"purpose": purpose},
            verbatim_url=verbatim_url,
            dont_cache=True,
        )

    def _reconciliation_message_request(self, message_id: str) -> scrapy.Request:
        purpose = "message-reconcile"
        encoded_id = quote(message_id, safe="")
        query = urlencode({"$select": ",".join(self.discovery_fields)})
        return self._request(
            f"{self.graph_root}/me/messages/{encoded_id}?{query}",
            callback=self.parse_reconciliation_message,
            purpose=purpose,
            cb_kwargs={"purpose": purpose, "message_id": message_id},
            dont_cache=True,
        )

    def _message_delta_start_request(self, folder_id: str) -> scrapy.Request:
        delta_link = self._delta_links.get(folder_id)
        self.crawler.stats.inc_value("msgloom/crawl/delta/folder_started_count")
        if delta_link:
            self.crawler.stats.inc_value(
                "msgloom/crawl/delta/folder_resumed_count"
            )
            return self._message_delta_request(
                delta_link,
                folder_id=folder_id,
                page_number=1,
            )

        self.crawler.stats.inc_value(
            "msgloom/crawl/delta/folder_initial_count"
        )
        encoded_id = quote(folder_id, safe="")
        query = urlencode({"$select": ",".join(self.discovery_fields)})
        return self._message_delta_request(
            f"{self.graph_root}/me/mailFolders/{encoded_id}/messages/delta?{query}",
            folder_id=folder_id,
            page_number=1,
        )

    def _message_delta_request(
        self,
        url: str,
        *,
        folder_id: str,
        page_number: int,
    ) -> scrapy.Request:
        purpose = "message-delta"
        return self._request(
            url,
            callback=self.parse_message_delta,
            purpose=purpose,
            cb_kwargs={
                "purpose": purpose,
                "folder_id": folder_id,
                "page_number": page_number,
            },
            dont_cache=True,
            verbatim_url=page_number > 1 or "$deltatoken=" in url,
            prefer=f'IdType="ImmutableId", odata.maxpagesize={self.page_size}',
        )

    def _delta_checkpoint_store(self) -> OutlookDeltaCheckpointStore:
        if self._checkpoint_store is None:
            self._checkpoint_store = OutlookDeltaCheckpointStore.from_crawler(
                self.crawler
            )
        return self._checkpoint_store

    def _full_requests(self, message_id: str):
        yield self._message_detail_request(message_id)
        yield self._message_mime_request(message_id)
        yield self._attachments_request(message_id, page_number=1)

    def _message_list_request(
        self,
        url: str,
        *,
        page_number: int,
        verbatim_url: bool = False,
    ) -> scrapy.Request:
        purpose = "message-list"
        return self._request(
            url,
            callback=self.parse,
            purpose=purpose,
            cb_kwargs={"purpose": purpose, "page_number": page_number},
            verbatim_url=verbatim_url,
        )

    def _message_detail_request(self, message_id: str) -> scrapy.Request:
        purpose = "message-detail"
        encoded_id = quote(message_id, safe="")
        query = urlencode({"$select": ",".join(self.full_fields)})
        return self._request(
            f"{self.graph_root}/me/messages/{encoded_id}?{query}",
            callback=self.parse_message_detail,
            purpose=purpose,
            cb_kwargs={"purpose": purpose, "message_id": message_id},
        )

    def _message_mime_request(self, message_id: str) -> scrapy.Request:
        purpose = "message-mime"
        encoded_id = quote(message_id, safe="")
        return self._request(
            f"{self.graph_root}/me/messages/{encoded_id}/$value",
            callback=self.parse_raw_evidence,
            purpose=purpose,
            cb_kwargs={"purpose": purpose, "message_id": message_id},
            accept="message/rfc822, */*",
        )

    def _attachments_request(
        self,
        message_id: str,
        *,
        url: str | None = None,
        page_number: int,
        verbatim_url: bool = False,
    ) -> scrapy.Request:
        purpose = "attachments-list"
        encoded_id = quote(message_id, safe="")
        return self._request(
            url or f"{self.graph_root}/me/messages/{encoded_id}/attachments",
            callback=self.parse_attachments,
            purpose=purpose,
            cb_kwargs={
                "purpose": purpose,
                "message_id": message_id,
                "page_number": page_number,
            },
            verbatim_url=verbatim_url,
        )

    def _attachment_raw_request(
        self,
        message_id: str,
        attachment_id: str,
    ) -> scrapy.Request:
        purpose = "attachment-raw"
        encoded_message_id = quote(message_id, safe="")
        encoded_attachment_id = quote(attachment_id, safe="")
        return self._request(
            f"{self.graph_root}/me/messages/{encoded_message_id}/attachments/"
            f"{encoded_attachment_id}/$value",
            callback=self.parse_raw_evidence,
            purpose=purpose,
            cb_kwargs={
                "purpose": purpose,
                "message_id": message_id,
                "attachment_id": attachment_id,
            },
            accept="*/*",
        )

    def _item_attachment_detail_request(
        self,
        message_id: str,
        attachment_id: str,
    ) -> scrapy.Request:
        purpose = "item-attachment-detail"
        encoded_message_id = quote(message_id, safe="")
        encoded_attachment_id = quote(attachment_id, safe="")
        query = urlencode({"$expand": "microsoft.graph.itemattachment/item"})
        return self._request(
            f"{self.graph_root}/me/messages/{encoded_message_id}/attachments/"
            f"{encoded_attachment_id}?{query}",
            callback=self.parse_attachment_detail,
            purpose=purpose,
            cb_kwargs={
                "purpose": purpose,
                "message_id": message_id,
                "attachment_id": attachment_id,
            },
        )

    def _request(
        self,
        url: str,
        *,
        callback,
        purpose: str,
        cb_kwargs: dict[str, Any],
        verbatim_url: bool = False,
        accept: str = "application/json",
        dont_cache: bool = False,
        prefer: str | None = 'IdType="ImmutableId"',
    ) -> scrapy.Request:
        headers = {"Accept": accept}
        if prefer is not None:
            headers["Prefer"] = prefer
        meta = {
            META_PURPOSE: purpose,
            META_RUN_ID: self.run_id,
        }
        if verbatim_url:
            meta["verbatim_url"] = True
        if dont_cache:
            meta["dont_cache"] = True
        return scrapy.Request(
            url,
            callback=callback,
            errback=self.errback,
            headers=headers,
            cb_kwargs=cb_kwargs,
            meta=meta,
        )

    def _message_item(
        self,
        message: dict[str, Any],
        source_response_url: str,
        observed_at: str,
        *,
        observation_kind: str,
        evidence_id: str | None,
    ) -> OutlookMailItem:
        return OutlookMailItem(
            message_id=message["id"],
            subject=message.get("subject"),
            sender_address=self._email_address(message.get("sender")),
            from_address=self._email_address(message.get("from")),
            received_date_time=message.get("receivedDateTime"),
            internet_message_id=message.get("internetMessageId"),
            conversation_id=message.get("conversationId"),
            parent_folder_id=message.get("parentFolderId"),
            importance=message.get("importance"),
            inference_classification=message.get("inferenceClassification"),
            is_read=message.get("isRead"),
            has_attachments=message.get("hasAttachments"),
            body_preview=message.get("bodyPreview"),
            raw=message,
            source_response_url=source_response_url,
            observed_at=observed_at,
            observation_kind=observation_kind,
            evidence_id=evidence_id,
            run_id=self.run_id,
        )

    @staticmethod
    def _evidence_id(response: scrapy.http.Response) -> str | None:
        value = response.meta.get(META_EVIDENCE_ID)
        return value if isinstance(value, str) else None

    @staticmethod
    def _attachment_type_name(attachment_type: str | None) -> str:
        if not attachment_type:
            return "unknown"
        return attachment_type.removeprefix("#microsoft.graph.").removeprefix(
            "microsoft.graph."
        )

    @staticmethod
    def _email_address(recipient: dict[str, Any] | None) -> str | None:
        if not recipient:
            return None
        return (recipient.get("emailAddress") or {}).get("address")

    @staticmethod
    def _bounded_int(
        raw: str,
        *,
        name: str,
        minimum: int,
        maximum: int | None = None,
    ) -> int:
        value = int(raw)
        if value < minimum or (maximum is not None and value > maximum):
            upper = f" and <= {maximum}" if maximum is not None else ""
            raise ValueError(f"{name} must be >= {minimum}{upper}")
        return value

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()
