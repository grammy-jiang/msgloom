from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class OutlookMailItem:
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
    message_id: str
    raw: dict[str, Any]
    source_response_url: str
    observed_at: str
    evidence_id: str | None
    run_id: str | None


@dataclass(slots=True)
class OutlookAttachmentItem:
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
    message_id: str
    surface: str
    status: str
    observed_at: str
    evidence_id: str | None
    profile_version: str | None = None


@dataclass(slots=True)
class OutlookDeltaCheckpointCandidateItem:
    run_id: str
    folder_id: str
    delta_link: str
    observed_at: str
    evidence_id: str | None


@dataclass(slots=True)
class AcquisitionFailureItem:
    url: str
    purpose: str
    error_type: str
    error_message: str
    observed_at: str
    message_id: str | None = None
    attachment_id: str | None = None
    folder_id: str | None = None
    evidence_id: str | None = None
    run_id: str | None = None
