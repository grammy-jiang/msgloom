"""Typed items produced by Outlook Mail spiders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OutlookMailItem:
    """One discovery, delta, or reconciliation observation of a message."""

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
    source_response_url: str
    observed_at: str
    observation_kind: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookMailDetailItem:
    """Full message JSON that also completes the versioned detail surface."""

    message_id: str
    raw: dict[str, Any]
    source_response_url: str
    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookAttachmentItem:
    """Attachment metadata from either inventory or expanded item detail."""

    message_id: str
    attachment_id: str
    attachment_type: str | None
    raw: dict[str, Any]
    source_response_url: str
    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookMailFolderItem:
    """One folder observation; absence from an inventory is not a deletion."""

    folder_id: str
    display_name: str | None
    parent_folder_id: str | None
    child_folder_count: int | None
    total_item_count: int | None
    unread_item_count: int | None
    is_hidden: bool | None
    raw: dict[str, Any]
    source_response_url: str
    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookMailRemovalItem:
    """
    Removal from one folder, without assuming the message is globally deleted.
    """

    message_id: str
    folder_id: str
    removed_reason: str | None
    raw: dict[str, Any]
    source_response_url: str
    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookMessageSurfaceItem:
    """
    A versioned acquisition result that future enrichment uses to plan work.
    """

    message_id: str
    surface: str
    status: str
    observed_at: str
    evidence_id: str | None
    profile_version: str | None = None


@dataclass(slots=True)
class OutlookFolderSnapshotCandidateItem:
    """Terminal recursive folder inventory awaiting idle-time promotion."""

    run_id: str
    observed_at: str
    evidence_id: str | None


@dataclass(slots=True)
class OutlookMessagePresenceSightingItem:
    """One lightweight message seen during whole-mailbox reconciliation."""

    run_id: str
    message_id: str
    observed_at: str
    evidence_id: str | None


@dataclass(slots=True)
class OutlookMessagePresenceCandidateItem:
    """Terminal whole-mailbox reconciliation awaiting presence promotion."""

    run_id: str
    observed_at: str
    evidence_id: str | None


@dataclass(slots=True)
class OutlookMailFolderRemovalItem:
    """Explicit folder deletion/removal reported by the mailFolder delta stream."""

    folder_id: str
    removed_reason: str | None
    raw: dict[str, Any]
    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookFolderDeltaCheckpointCandidateItem:
    """Terminal mailFolder delta cursor awaiting idle-time promotion."""

    run_id: str
    delta_link: str
    observed_at: str
    evidence_id: str | None


@dataclass(slots=True)
class OutlookDeltaCheckpointCandidateItem:
    """
    A final-page cursor pending whole-run validation by the idle extension.
    """

    run_id: str
    folder_id: str
    delta_link: str
    observed_at: str
    evidence_id: str | None


__all__ = [
    "OutlookAttachmentItem",
    "OutlookDeltaCheckpointCandidateItem",
    "OutlookFolderDeltaCheckpointCandidateItem",
    "OutlookFolderSnapshotCandidateItem",
    "OutlookMailDetailItem",
    "OutlookMailFolderItem",
    "OutlookMailFolderRemovalItem",
    "OutlookMailItem",
    "OutlookMailRemovalItem",
    "OutlookMessagePresenceCandidateItem",
    "OutlookMessagePresenceSightingItem",
    "OutlookMessageSurfaceItem",
]
