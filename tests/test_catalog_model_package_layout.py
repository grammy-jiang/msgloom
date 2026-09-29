"""Lock SQLAlchemy models into acquisition and Outlook resource domains."""

from __future__ import annotations

from pathlib import Path

import pytest

from message_ingest.catalog.models import Base
from message_ingest.catalog.models.acquisition import (
    RawHttpEvidence,
    SourceBinding,
    SourceTargetBinding,
)
from message_ingest.catalog.models.microsoft.outlook.calendar import (
    CalendarDeltaCheckpoint,
    CalendarDeltaCheckpointCandidate,
    CalendarDeltaEventState,
    CalendarDeltaObservation,
    CalendarEventAttachmentRecord,
    CalendarEventObservation,
    CalendarEventRecord,
    CalendarEventSighting,
    CalendarEventSurface,
    CalendarRecord,
    CalendarSeriesTopologyRecord,
)
from message_ingest.catalog.models.microsoft.outlook.email import (
    AttachmentRecord,
    DeltaCheckpoint,
    DeltaCheckpointCandidate,
    FolderDeltaCheckpoint,
    FolderDeltaCheckpointCandidate,
    MailFolderPresence,
    MailFolderRecord,
    MailFolderSighting,
    MailFolderSnapshotCandidate,
    MessageObservation,
    MessagePresence,
    MessagePresenceCandidate,
    MessagePresenceSighting,
    MessageRecord,
    MessageSurface,
)

EXPECTED_TABLES = {
    "attachments",
    "calendar_delta_checkpoint_candidates",
    "calendar_delta_checkpoints",
    "calendar_delta_event_states",
    "calendar_delta_observations",
    "calendar_event_attachments",
    "calendar_event_observations",
    "calendar_event_sightings",
    "calendar_event_surfaces",
    "calendar_events",
    "calendars",
    "message_presence_sightings",
    "message_presence_candidates",
    "message_presence",
    "mail_folder_snapshot_candidates",
    "mail_folder_sightings",
    "mail_folder_presence",
    "folder_delta_checkpoints",
    "folder_delta_checkpoint_candidates",
    "calendar_series_topologies",
    "delta_checkpoint_candidates",
    "delta_checkpoints",
    "mail_folders",
    "message_observations",
    "message_surfaces",
    "messages",
    "raw_http_evidence",
    "source_bindings",
    "source_target_bindings",
    "todo_task_lists",
    "todo_tasks",
    "todo_checklist_items",
    "todo_linked_resources",
}


def test_model_package_registers_complete_existing_schema() -> None:
    if set(Base.metadata.tables) != EXPECTED_TABLES:
        pytest.fail(
            f"Catalog metadata changed during model split: {sorted(Base.metadata.tables)!r}"
        )


def test_models_live_in_expected_domain_modules() -> None:
    expected = {
        SourceBinding: "message_ingest.catalog.models.acquisition",
        SourceTargetBinding: "message_ingest.catalog.models.acquisition",
        RawHttpEvidence: "message_ingest.catalog.models.acquisition",
        CalendarRecord: "message_ingest.catalog.models.microsoft.outlook.calendar",
        CalendarEventRecord: "message_ingest.catalog.models.microsoft.outlook.calendar",
        CalendarEventSighting: "message_ingest.catalog.models.microsoft.outlook.calendar",
        CalendarEventSurface: "message_ingest.catalog.models.microsoft.outlook.calendar",
        CalendarEventObservation: "message_ingest.catalog.models.microsoft.outlook.calendar",
        CalendarEventAttachmentRecord: "message_ingest.catalog.models.microsoft.outlook.calendar",
        CalendarDeltaCheckpoint: "message_ingest.catalog.models.microsoft.outlook.calendar",
        CalendarDeltaCheckpointCandidate: "message_ingest.catalog.models.microsoft.outlook.calendar",
        CalendarDeltaObservation: "message_ingest.catalog.models.microsoft.outlook.calendar",
        CalendarDeltaEventState: "message_ingest.catalog.models.microsoft.outlook.calendar",
        MessagePresenceSighting: "message_ingest.catalog.models.microsoft.outlook.email",
        MessagePresenceCandidate: "message_ingest.catalog.models.microsoft.outlook.email",
        MessagePresence: "message_ingest.catalog.models.microsoft.outlook.email",
        MailFolderSnapshotCandidate: "message_ingest.catalog.models.microsoft.outlook.email",
        MailFolderSighting: "message_ingest.catalog.models.microsoft.outlook.email",
        MailFolderPresence: "message_ingest.catalog.models.microsoft.outlook.email",
        FolderDeltaCheckpointCandidate: "message_ingest.catalog.models.microsoft.outlook.email",
        FolderDeltaCheckpoint: "message_ingest.catalog.models.microsoft.outlook.email",
        CalendarSeriesTopologyRecord: "message_ingest.catalog.models.microsoft.outlook.calendar",
        MessageRecord: "message_ingest.catalog.models.microsoft.outlook.email",
        MessageObservation: "message_ingest.catalog.models.microsoft.outlook.email",
        MessageSurface: "message_ingest.catalog.models.microsoft.outlook.email",
        AttachmentRecord: "message_ingest.catalog.models.microsoft.outlook.email",
        MailFolderRecord: "message_ingest.catalog.models.microsoft.outlook.email",
        DeltaCheckpoint: "message_ingest.catalog.models.microsoft.outlook.email",
        DeltaCheckpointCandidate: "message_ingest.catalog.models.microsoft.outlook.email",
    }
    for model, module in expected.items():
        if model.__module__ != module:
            pytest.fail(f"{model.__name__} belongs to {model.__module__!r}")


def test_legacy_flat_models_module_is_gone() -> None:
    legacy = Path(__file__).parents[1] / "message_ingest" / "catalog" / "models.py"
    if legacy.exists():
        pytest.fail(f"Legacy flat models module must not return: {legacy}")
