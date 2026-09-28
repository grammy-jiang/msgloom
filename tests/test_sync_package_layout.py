"""Lock synchronization state and Scrapy lifecycle adapters into separate domains."""

from __future__ import annotations

from pathlib import Path

import pytest

from message_ingest.extensions.microsoft import outlook as extension_outlook
from message_ingest.extensions.microsoft.outlook import (
    calendar as calendar_extensions,
)
from message_ingest.extensions.microsoft.outlook import (
    email as email_extensions,
)
from message_ingest.sync import microsoft as sync_microsoft
from message_ingest.sync.microsoft import outlook as sync_outlook
from message_ingest.sync.microsoft.outlook import (
    calendar as calendar_sync,
)
from message_ingest.sync.microsoft.outlook import (
    email as email_sync,
)


def test_sync_packages_expose_only_domain_surfaces() -> None:
    if sync_microsoft.__all__ != ["outlook"]:
        pytest.fail(f"Unexpected Microsoft sync exports: {sync_microsoft.__all__!r}")
    if sync_outlook.__all__ != ["calendar", "email"]:
        pytest.fail(f"Unexpected Outlook sync exports: {sync_outlook.__all__!r}")
    if email_sync.__all__ != ["OutlookDeltaCheckpointStore"]:
        pytest.fail(f"Unexpected Outlook Mail sync exports: {email_sync.__all__!r}")
    if calendar_sync.__all__ != [
        "CalendarDeltaCandidateState",
        "CalendarDeltaCheckpointConflict",
        "CalendarDeltaCheckpointState",
        "CalendarDeltaCheckpointStore",
        "apply_calendar_delta_state",
    ]:
        pytest.fail(f"Unexpected Calendar sync exports: {calendar_sync.__all__!r}")


def test_checkpoint_extensions_expose_only_framework_adapters() -> None:
    if extension_outlook.__all__ != ["calendar", "email"]:
        pytest.fail(
            f"Unexpected Outlook extension exports: {extension_outlook.__all__!r}"
        )
    if email_extensions.__all__ != ["OutlookDeltaCheckpointExtension"]:
        pytest.fail(
            f"Unexpected Outlook Mail extension exports: {email_extensions.__all__!r}"
        )
    if calendar_extensions.__all__ != [
        "CalendarDeltaCheckpointExtension",
        "CalendarDeltaSpiderState",
    ]:
        pytest.fail(
            f"Unexpected Calendar extension exports: {calendar_extensions.__all__!r}"
        )


def test_legacy_root_checkpoint_modules_are_gone() -> None:
    root = Path(__file__).parents[1] / "message_ingest"
    legacy = [
        root / "checkpoints.py",
        root / "calendar_checkpoints.py",
        root / "calendar_delta_state.py",
        root / "extensions" / "delta_checkpoint.py",
        root / "extensions" / "calendar_delta_checkpoint.py",
    ]
    existing = [str(path) for path in legacy if path.exists()]
    if existing:
        pytest.fail(f"Legacy checkpoint modules must not return: {existing!r}")
