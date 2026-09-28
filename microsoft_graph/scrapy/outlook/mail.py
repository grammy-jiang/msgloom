"""Reusable Outlook Mail scopes, fields, paths, and representation."""

from typing import ClassVar
from urllib.parse import quote

from .mailbox import OutlookMailboxSpider


class OutlookMailSpider(OutlookMailboxSpider):
    """Acquire Mail with immutable IDs and own/shared read permissions."""

    graph_prefer = 'IdType="ImmutableId"'
    graph_permissions: ClassVar[tuple[str, ...]] = ("Mail.Read",)
    shared_graph_permissions: ClassVar[tuple[str, ...]] = ("Mail.Read.Shared",)
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

    def _message_path(self, message_id: str) -> str:
        """Return the mailbox-relative path for one encoded message ID."""
        return f"{self._mailbox_path()}/messages/{quote(message_id, safe='')}"
