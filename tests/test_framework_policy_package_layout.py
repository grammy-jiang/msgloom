"""Lock Scrapy request-identity and observability policies out of the project root."""

from __future__ import annotations

from pathlib import Path

import pytest

from message_ingest import fingerprints, observability
from message_ingest.fingerprints import microsoft, microsoft_graph
from message_ingest.fingerprints.microsoft import outlook
from message_ingest.fingerprints.microsoft.outlook import calendar


def test_fingerprint_packages_expose_only_domain_surfaces() -> None:
    if fingerprints.__all__ != ["microsoft", "microsoft_graph"]:
        pytest.fail(f"Unexpected fingerprint exports: {fingerprints.__all__!r}")
    if microsoft.__all__ != ["outlook"]:
        pytest.fail(f"Unexpected Microsoft fingerprint exports: {microsoft.__all__!r}")
    if outlook.__all__ != ["calendar"]:
        pytest.fail(f"Unexpected Outlook fingerprint exports: {outlook.__all__!r}")
    if microsoft_graph.__all__ != ["RepresentationAwareRequestFingerprinter"]:
        pytest.fail(
            f"Unexpected Graph fingerprint exports: {microsoft_graph.__all__!r}"
        )
    if calendar.__all__ != ["CalendarDeltaRequestFingerprinter"]:
        pytest.fail(f"Unexpected Calendar fingerprint exports: {calendar.__all__!r}")


def test_fingerprint_classes_live_in_their_policy_modules() -> None:
    if microsoft_graph.RepresentationAwareRequestFingerprinter.__module__ != (
        "message_ingest.fingerprints.microsoft_graph"
    ):
        pytest.fail("Graph request identity policy moved outside its domain")
    if calendar.CalendarDeltaRequestFingerprinter.__module__ != (
        "message_ingest.fingerprints.microsoft.outlook.calendar"
    ):
        pytest.fail("Calendar delta request identity policy moved outside its domain")


def test_observability_exports_public_formatter_and_summary_helper() -> None:
    if observability.__all__ != ["MessageIngestLogFormatter", "summarize_item"]:
        pytest.fail(f"Unexpected observability exports: {observability.__all__!r}")


def test_legacy_root_policy_modules_are_gone() -> None:
    root = Path(__file__).parents[1] / "message_ingest"
    legacy = [root / "fingerprints.py", root / "logformatter.py"]
    existing = [str(path) for path in legacy if path.exists()]
    if existing:
        pytest.fail(f"Legacy root policy modules must not return: {existing!r}")
