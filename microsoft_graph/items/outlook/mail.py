"""Optional Mail projections that retain the complete provider resource."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from microsoft_graph.protocol import graph_object


def _email_address(recipient: dict[str, Any] | None) -> str | None:
    """Read the optional address inside a Graph recipient."""
    if not recipient:
        return None
    return (recipient.get("emailAddress") or {}).get("address")


@dataclass(slots=True)
class OutlookMessageItem:
    """
    Common Mail fields and unchanged message JSON.

    :meth:`from_graph` maps partial Graph representations. Missing optional
    fields become ``None``; it does not infer completeness or normalize mail
    conversations. Extra keyword arguments supply subclass fields.
    """

    message_id: str
    subject: str | None
    sender_address: str | None
    from_address: str | None
    received_date_time: str | None
    internet_message_id: str | None
    conversation_id: str | None
    parent_folder_id: str | None
    importance: str | None
    inference_classification: str | None
    is_read: bool | None
    has_attachments: bool | None
    body_preview: str | None
    raw: dict[str, Any]

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map an object with an ``id`` and keep its complete JSON."""
        raw = graph_object(resource, context="Outlook message")
        return cls(
            message_id=raw["id"],
            subject=raw.get("subject"),
            sender_address=_email_address(raw.get("sender")),
            from_address=_email_address(raw.get("from")),
            received_date_time=raw.get("receivedDateTime"),
            internet_message_id=raw.get("internetMessageId"),
            conversation_id=raw.get("conversationId"),
            parent_folder_id=raw.get("parentFolderId"),
            importance=raw.get("importance"),
            inference_classification=raw.get("inferenceClassification"),
            is_read=raw.get("isRead"),
            has_attachments=raw.get("hasAttachments"),
            body_preview=raw.get("bodyPreview"),
            raw=raw,
            **kwargs,
        )


@dataclass(slots=True)
class OutlookMailFolderItem:
    """A mailFolder projection with the unmodified provider object."""

    folder_id: str
    display_name: str | None
    parent_folder_id: str | None
    child_folder_count: int | None
    total_item_count: int | None
    unread_item_count: int | None
    is_hidden: bool | None
    raw: dict[str, Any]

    @classmethod
    def from_graph(cls, resource: dict[str, Any], **kwargs: Any) -> Self:
        """Map a partial folder; keyword arguments supply subclass fields."""
        raw = graph_object(resource, context="Outlook mailFolder")
        return cls(
            folder_id=raw["id"],
            display_name=raw.get("displayName"),
            parent_folder_id=raw.get("parentFolderId"),
            child_folder_count=raw.get("childFolderCount"),
            total_item_count=raw.get("totalItemCount"),
            unread_item_count=raw.get("unreadItemCount"),
            is_hidden=raw.get("isHidden"),
            raw=raw,
            **kwargs,
        )


@dataclass(slots=True)
class OutlookAttachmentItem:
    """Attachment identity, provider type, and JSON under one message."""

    message_id: str
    attachment_id: str
    attachment_type: str | None
    raw: dict[str, Any]

    @classmethod
    def from_graph(
        cls, resource: dict[str, Any], *, message_id: str, **kwargs: Any
    ) -> Self:
        """Keep attachment content and nested items unchanged."""
        raw = graph_object(resource, context="Outlook attachment")
        return cls(
            message_id=message_id,
            attachment_id=raw["id"],
            attachment_type=raw.get("@odata.type"),
            raw=raw,
            **kwargs,
        )
