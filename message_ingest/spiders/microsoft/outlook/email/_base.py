"""Outlook Mail resource contracts layered on Microsoft Graph transport."""

from __future__ import annotations

from abc import ABC
from typing import Any, ClassVar

import scrapy

from message_ingest.items.microsoft.outlook.email import OutlookMailItem
from message_ingest.spiders.microsoft.outlook._mailbox import OutlookMailboxSpider


class OutlookMailSpider(OutlookMailboxSpider, ABC):
    """
    Share Outlook Mail representation and item projection across acquisition modes.

    Microsoft Graph request/evidence/failure behavior lives in the provider
    base. Mail keeps its own delegated scope, immutable-ID preference, semantic
    fields, and callback context.
    """

    graph_permissions: ClassVar[tuple[str, ...]] = ("Mail.Read",)
    shared_graph_permissions: ClassVar[tuple[str, ...]] = ("Mail.Read.Shared",)
    failure_context_keys: ClassVar[tuple[str, ...]] = (
        "message_id",
        "attachment_id",
        "folder_id",
    )

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
        download_maxsize: int | None = None,
    ) -> scrapy.Request:
        """Build a Graph request with Outlook's immutable-ID preference."""
        return super()._request(
            url,
            callback=callback,
            purpose=purpose,
            cb_kwargs=cb_kwargs,
            verbatim_url=verbatim_url,
            accept=accept,
            dont_cache=dont_cache,
            prefer=prefer,
            download_maxsize=download_maxsize,
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
        """Retain the raw message beside searchable Mail projections."""
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
    def _email_address(recipient: dict[str, Any] | None) -> str | None:
        """Return the optional nested Graph email address."""
        if not recipient:
            return None
        return (recipient.get("emailAddress") or {}).get("address")
