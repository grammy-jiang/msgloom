"""Lock Outlook Mail lifecycle extensions into their resource domain."""

from __future__ import annotations

from pathlib import Path

import pytest

from message_ingest.extensions.microsoft.outlook import email
from message_ingest.extensions.microsoft.outlook.email.status import (
    OutlookCrawlStatusExtension,
)


def test_outlook_mail_extension_surface_is_resource_scoped() -> None:
    if email.__all__ != [
        "OutlookCrawlStatusExtension",
        "OutlookDeltaCheckpointExtension",
    ]:
        pytest.fail(f"Unexpected Outlook Mail extension exports: {email.__all__!r}")
    if OutlookCrawlStatusExtension.__module__ != (
        "message_ingest.extensions.microsoft.outlook.email.status"
    ):
        pytest.fail("Outlook Mail status extension moved outside its resource domain")


def test_legacy_root_status_extension_is_gone() -> None:
    legacy = Path(__file__).parents[1] / "message_ingest" / "extensions" / "status.py"
    if legacy.exists():
        pytest.fail(f"Legacy root status extension must not return: {legacy}")
