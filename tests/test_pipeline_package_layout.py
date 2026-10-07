"""Lock Scrapy persistence pipelines into resource domains."""

from __future__ import annotations

from pathlib import Path

import pytest

from message_ingest import pipelines
from message_ingest.pipelines import microsoft
from message_ingest.pipelines.microsoft import outlook
from message_ingest.pipelines.microsoft.outlook import (
    OutlookCalendarPipeline,
    OutlookMailPipeline,
)


def test_pipeline_packages_expose_resource_surfaces() -> None:
    if pipelines.__all__ != ["evidence", "microsoft"]:
        pytest.fail(f"Unexpected pipeline exports: {pipelines.__all__!r}")
    if microsoft.__all__ != ["outlook"]:
        pytest.fail(f"Unexpected Microsoft pipeline exports: {microsoft.__all__!r}")
    if outlook.__all__ != ["OutlookCalendarPipeline", "OutlookMailPipeline"]:
        pytest.fail(f"Unexpected Outlook pipeline exports: {outlook.__all__!r}")


def test_resource_pipelines_live_in_domain_modules() -> None:
    if (
        OutlookMailPipeline.__module__
        != "message_ingest.pipelines.microsoft.outlook.email"
    ):
        pytest.fail("Outlook Mail pipeline moved outside its resource domain")
    if OutlookCalendarPipeline.__module__ != (
        "message_ingest.pipelines.microsoft.outlook.calendar"
    ):
        pytest.fail("Outlook Calendar pipeline moved outside its resource domain")


def test_legacy_resource_pipeline_modules_are_gone() -> None:
    root = Path(__file__).parents[1] / "message_ingest" / "pipelines"
    legacy = [
        root / "catalog.py",
        root / "calendar.py",
        root / "calendar_attachments.py",
    ]
    existing = [str(path) for path in legacy if path.exists()]
    if existing:
        pytest.fail(f"Legacy resource pipeline modules must not return: {existing!r}")
