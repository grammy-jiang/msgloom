"""Lock the domain-oriented item package layout."""

from __future__ import annotations

from pathlib import Path

import pytest

from message_ingest import items
from message_ingest.items import acquisition, microsoft
from message_ingest.items.microsoft import outlook
from message_ingest.items.microsoft.outlook import calendar, email


def test_item_packages_expose_only_declared_domain_surfaces() -> None:
    if items.__all__ != ["acquisition", "microsoft"]:
        pytest.fail(f"Unexpected item package exports: {items.__all__!r}")
    if microsoft.__all__ != ["outlook"]:
        pytest.fail(f"Unexpected Microsoft item exports: {microsoft.__all__!r}")
    if outlook.__all__ != ["calendar", "email"]:
        pytest.fail(f"Unexpected Outlook item exports: {outlook.__all__!r}")


def test_item_classes_live_in_their_domain_modules() -> None:
    expected = {
        acquisition.RawHttpEvidenceItem: "message_ingest.items.acquisition",
        acquisition.AcquisitionFailureItem: "message_ingest.items.acquisition",
        email.OutlookMailItem: "message_ingest.items.microsoft.outlook.email",
        email.OutlookMailDetailItem: "message_ingest.items.microsoft.outlook.email",
        email.OutlookAttachmentItem: "message_ingest.items.microsoft.outlook.email",
        email.OutlookMailFolderItem: "message_ingest.items.microsoft.outlook.email",
        email.OutlookMailRemovalItem: "message_ingest.items.microsoft.outlook.email",
        email.OutlookMessageSurfaceItem: "message_ingest.items.microsoft.outlook.email",
        email.OutlookDeltaCheckpointCandidateItem: (
            "message_ingest.items.microsoft.outlook.email"
        ),
        calendar.OutlookCalendarItem: "message_ingest.items.microsoft.outlook.calendar",
        calendar.OutlookCalendarEventItem: (
            "message_ingest.items.microsoft.outlook.calendar"
        ),
        calendar.OutlookCalendarAttachmentItem: (
            "message_ingest.items.microsoft.outlook.calendar"
        ),
        calendar.OutlookCalendarAttachmentContentItem: (
            "message_ingest.items.microsoft.outlook.calendar"
        ),
        calendar.OutlookCalendarDeltaObservationItem: (
            "message_ingest.items.microsoft.outlook.calendar"
        ),
        calendar.OutlookCalendarDeltaCheckpointCandidateItem: (
            "message_ingest.items.microsoft.outlook.calendar"
        ),
    }
    for cls, module in expected.items():
        if cls.__module__ != module:
            pytest.fail(
                f"{cls.__name__} belongs to {cls.__module__!r}, expected {module!r}"
            )


def test_flat_items_module_is_gone() -> None:
    project_root = Path(__file__).parents[1]
    flat_module = project_root / "message_ingest" / "items.py"
    if flat_module.exists():
        pytest.fail(f"Flat items module must not return: {flat_module}")
