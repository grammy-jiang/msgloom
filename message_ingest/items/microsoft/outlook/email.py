"""Typed items produced by Outlook Mail spiders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from microsoft_graph.items.outlook import (
    OutlookAttachmentItem as GraphOutlookAttachmentItem,
)
from microsoft_graph.items.outlook import (
    OutlookMailFolderItem as GraphOutlookMailFolderItem,
)
from microsoft_graph.items.outlook import (
    OutlookMessageItem as GraphOutlookMessageItem,
)


@dataclass(slots=True)
class OutlookMailItem(GraphOutlookMessageItem):
    """One discovery, delta, or reconciliation observation of a message."""

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
    selection_id: str | None = None


@dataclass(slots=True)
class OutlookAttachmentItem(GraphOutlookAttachmentItem):
    """Attachment metadata from either inventory or expanded item detail."""

    source_response_url: str
    observed_at: str
    evidence_id: str | None
    run_id: str | None
    resource_version: str | None = None
    primary_observed_at: str | None = None
    selection_id: str | None = None
    parent_evidence_id: str | None = None
    capture_id: str | None = None


@dataclass(slots=True)
class OutlookMailFolderItem(GraphOutlookMailFolderItem):
    """One folder observation; absence from an inventory is not a deletion."""

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
    run_id: str | None
    profile_version: str | None = None
    resource_version: str | None = None
    primary_observed_at: str | None = None
    selection_id: str | None = None
    parent_evidence_id: str | None = None
    capture_id: str | None = None


@dataclass(slots=True)
class OutlookMailInventoryPageItem:
    """One native traversal page with exact selected metadata captures."""

    message_id: str
    selection_id: str
    resource_version: str
    parent_evidence_id: str
    inventory_id: str
    page_id: str
    previous_page_id: str | None
    page_number: int
    member_capture_ids: tuple[str, ...]
    status: str
    profile_version: str
    evidence_id: str
    observed_at: str
    run_id: str


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
    """Explicit folder removal reported by the mailFolder delta stream."""

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
    "OutlookMailInventoryPageItem",
    "OutlookMailItem",
    "OutlookMailRemovalItem",
    "OutlookMessagePresenceCandidateItem",
    "OutlookMessagePresenceSightingItem",
    "OutlookMessageSurfaceItem",
]
