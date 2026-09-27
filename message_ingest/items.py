"""
Typed contracts between spiders and persistence components.

``raw`` retains the provider JSON; indexed fields are only projections.
Semantic items reference a :class:`~message_ingest.items.RawHttpEvidenceItem`
emitted earlier by the same callback. Pipelines may replace provisional
evidence IDs/timestamps during cache replay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RawHttpEvidenceItem:
    """Complete Spider-visible HTTP request/response evidence for a provider."""

    evidence_id: str
    run_id: str | None
    purpose: str
    observed_at: str
    origin: str
    request_fingerprint: str
    request_url: str
    request_method: str
    request_headers: dict[str, list[str]]
    request_body: bytes
    response_url: str | None
    response_status: int | None
    response_headers: dict[str, list[str]]
    response_body: bytes
    response_flags: list[str]
    error_type: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class OutlookCalendarItem:
    """One observation of a calendar visible to the signed-in user."""

    calendar_id: str
    raw: dict[str, Any]
    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookCalendarEventItem:
    """One observation of an event in a declared Calendar scope."""

    event_id: str
    raw: dict[str, Any]
    observed_at: str
    evidence_id: str | None
    run_id: str | None
    calendar_id: str = "default"
    observation_kind: str = "window"


@dataclass(slots=True)
class OutlookCalendarAttachmentItem:
    """One attachment metadata/content observation for a Calendar event."""

    event_id: str
    attachment_id: str
    attachment_type: str | None
    raw: dict[str, Any]
    observed_at: str
    evidence_id: str | None
    run_id: str | None
    calendar_id: str = "default"
    content_bytes_present: bool = False


@dataclass(slots=True)
class OutlookCalendarAttachmentContentItem:
    """Successful raw-content acquisition for one Calendar attachment."""

    event_id: str
    attachment_id: str
    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookCalendarDeltaObservationItem:
    """One ordered event entry from a fixed Calendar delta window."""

    event_id: str
    kind: str
    raw: dict[str, Any]
    observed_at: str
    evidence_id: str
    run_id: str
    attempt: int
    page_number: int
    entry_index: int
    start_datetime: str
    end_datetime: str
    removed_reason: str | None = None
    calendar_scope: str = "default"


@dataclass(slots=True)
class OutlookCalendarDeltaCheckpointCandidateItem:
    """Terminal Calendar delta cursor pending idle-time promotion."""

    run_id: str
    attempt: int
    base_revision: int | None
    delta_link: str
    observed_at: str
    evidence_id: str
    start_datetime: str
    end_datetime: str
    calendar_scope: str = "default"


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
class OutlookDeltaCheckpointCandidateItem:
    """
    A final-page cursor pending whole-run validation by the idle extension.
    """

    run_id: str
    folder_id: str
    delta_link: str
    observed_at: str
    evidence_id: str | None


@dataclass(slots=True)
class AcquisitionFailureItem:
    """
    An exhausted acquisition error linked to raw evidence and resource context.
    """

    url: str
    purpose: str
    error_type: str
    error_message: str
    observed_at: str
    context: dict[str, str] = field(default_factory=dict)
    evidence_id: str | None = None
    run_id: str | None = None
