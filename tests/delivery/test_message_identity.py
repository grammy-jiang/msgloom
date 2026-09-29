"""Verify that each saved report part gets a distinct MIME identity."""

from __future__ import annotations

import asyncio
import email
from email import policy
from pathlib import Path

import pytest

from msgloom.contracts import VersionRef
from msgloom.delivery import build_mime
from msgloom.reporting import SavedReport
from tests.delivery.helpers import build_report, open_store


def _saved_report(tmp_path: Path) -> SavedReport:
    async def exercise() -> SavedReport:
        store = await open_store(tmp_path / "identity.sqlite3")
        try:
            _ref, report = await build_report(store)
        finally:
            await store.close()
        return report

    return asyncio.run(exercise())


def _identity(report: SavedReport) -> tuple[str, str]:
    part = report.parts[0]
    raw = build_mime(report, part, report.destination.destination_identity)
    message = email.message_from_bytes(raw, policy=policy.default)
    return str(message["Message-ID"]), message.get_boundary() or ""


def test_colon_placement_cannot_alias_report_identity(tmp_path: Path) -> None:
    """Distinct report references never share a Message-ID or boundary."""
    report = _saved_report(tmp_path)
    one = report.model_copy(update={"report_ref": VersionRef("report", "a:b", "c")})
    two = report.model_copy(update={"report_ref": VersionRef("report", "a", "b:c")})
    first, second = _identity(one), _identity(two)
    if first[0] == second[0] or first[1] == second[1]:
        pytest.fail("colon placement aliased two report MIME identities")


def test_policy_version_is_part_of_message_identity(tmp_path: Path) -> None:
    """A different policy version yields a different Message-ID."""
    report = _saved_report(tmp_path)
    changed = report.model_copy(
        update={
            "policy_ref": VersionRef(
                report.policy_ref.kind, report.policy_ref.identity, "other"
            )
        }
    )
    if _identity(report)[0] == _identity(changed)[0]:
        pytest.fail("policy version did not change the Message-ID")
    if _identity(report) != _identity(report):
        pytest.fail("MIME identity is not deterministic for one saved part")
