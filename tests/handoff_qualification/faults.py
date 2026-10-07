"""
Qualification helpers prove release faults reached the publication boundary.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

_RELEASE_INSERT = "insert into acquisition_release_entries"
_MARKER_ENV = "MSGLOOM_QUALIFICATION_RELEASE_MARKER"


@dataclass(frozen=True)
class FailureSignature:
    """Describe one provider's expected publication-failure surface."""

    reason: str
    error_line: str


FAILURE_SIGNATURES = {
    "todo": FailureSignature(
        reason="todo_snapshot_promotion_failed",
        error_line="To Do snapshot promotion blocked: error_type=IntegrityError",
    ),
    "contacts": FailureSignature(
        reason="contacts_snapshot_promotion_failed",
        error_line="Contacts snapshot promotion failed: error_type=IntegrityError",
    ),
    "calendar": FailureSignature(
        reason="calendar_checkpoint_commit_failed",
        error_line=(
            "Unable to commit Calendar delta checkpoint: error_type=IntegrityError"
        ),
    ),
    "onedrive": FailureSignature(
        reason="onedrive_checkpoint_promotion_failed",
        error_line="OneDrive checkpoint promotion failed: error_type=IntegrityError",
    ),
}


def arm_release_probe(root: Path, monkeypatch) -> Path:
    """
    Arm child-process SQL instrumentation for the exact release-entry insert.

    The probe runs through Python's normal sitecustomize hook only in
    subprocesses spawned by the current test. It observes SQL execution and
    never replaces a store, transaction, or production component.
    """
    marker = root / "qualification-release-entry-insert.reached"
    marker.unlink(missing_ok=True)
    probe = Path(__file__).with_name("release_probe")
    inherited = os.environ.get("PYTHONPATH")
    pythonpath = str(probe)
    if inherited:
        pythonpath += os.pathsep + inherited
    monkeypatch.setenv("PYTHONPATH", pythonpath)
    monkeypatch.setenv(_MARKER_ENV, str(marker))
    return marker


def disarm_release_probe(monkeypatch) -> None:
    """Stop marker writes before the healthy recovery crawl."""
    monkeypatch.delenv(_MARKER_ENV, raising=False)


def release_failure_problem(
    result: subprocess.CompletedProcess[str],
    marker: Path,
    provider: str,
) -> str | None:
    """
    Return why a native crawl did not prove the intended injected failure.

    A qualifying failure must expose the provider-specific promotion boundary,
    classify the database exception as IntegrityError, and leave the
    fixture-owned marker proving the exact release-entry insert was attempted.
    """
    signature = FAILURE_SIGNATURES[provider]
    if result.returncode != 1:
        return f"{provider} publication fault returned {result.returncode}, not 1"
    if signature.error_line not in result.stderr:
        return f"{provider} did not report its expected IntegrityError"
    if signature.reason not in result.stderr:
        return f"{provider} did not report its promotion-failure reason"
    if not marker.is_file():
        return f"{provider} did not reach the release-entry INSERT boundary"
    statement = " ".join(marker.read_text().lower().split())
    if _RELEASE_INSERT not in statement:
        return f"{provider} reached marker does not name the release-entry INSERT"
    return None
