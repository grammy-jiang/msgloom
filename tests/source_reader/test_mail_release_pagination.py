"""Selected Mail pagination reads only retained inventory chains."""

import hashlib
import sqlite3

import pytest

from msgloom.sources import SourceEvidenceError, SourceReferenceError
from tests.source_reader.release_mail_helpers import (
    mail_catalog as mail_catalog,  # noqa: PLC0414 - pytest fixture registration
)
from tests.source_reader.release_mail_helpers import read, release, selected_inventory


def test_selected_two_page_inventory_reconstructs_every_named_member(mail_catalog):
    seq = release(mail_catalog, selected_inventory(mail_catalog))
    result = read(mail_catalog, seq)
    names = {item.name for item in result.selection.record.attachments}
    if names != {"page-1.txt", "page-2.txt"}:
        pytest.fail("Selected predecessor chain lost or added members")


def test_selected_inventory_missing_named_metadata_fails_closed(mail_catalog):
    facts = selected_inventory(mail_catalog)
    facts = [fact for fact in facts if fact.resource_identity != "a1"]
    with pytest.raises(SourceReferenceError, match="membership"):
        read(mail_catalog, release(mail_catalog, facts))


@pytest.mark.parametrize("terminal_status", ["acquired", "unavailable"])
def test_selected_inventory_verifies_nonterminal_page_bytes(
    mail_catalog,
    terminal_status,
):
    seq = release(
        mail_catalog,
        selected_inventory(mail_catalog, terminal_status=terminal_status),
    )
    with sqlite3.connect(mail_catalog["database"]) as connection:
        path = connection.execute(
            "SELECT response_body_path FROM raw_http_evidence WHERE evidence_id=?",
            ("page-1",),
        ).fetchone()[0]
    from pathlib import Path

    saved = Path(path)
    before = hashlib.sha256(saved.read_bytes()).hexdigest()
    saved.write_bytes(b"tampered predecessor")
    if hashlib.sha256(saved.read_bytes()).hexdigest() == before:
        pytest.fail("Fixture did not change predecessor bytes")
    with pytest.raises(SourceEvidenceError):
        read(mail_catalog, seq)


@pytest.mark.parametrize(
    "status",
    ["unavailable", "unauthorized", "unsupported", "omitted_size_limit"],
)
def test_selected_inventory_terminal_limitation_keeps_partial_members_unreleased(
    mail_catalog,
    status,
):
    """A terminal failure retains provenance without claiming partial members."""
    facts = selected_inventory(mail_catalog, terminal_status=status)
    result = read(mail_catalog, release(mail_catalog, facts))
    if result.selection.record.attachments:
        pytest.fail("Incomplete inventory released partial attachment members")
    codes = {limitation.code for limitation in result.selection.record.limitations}
    if f"mail-{status}" not in codes:
        pytest.fail("Terminal inventory limitation was lost")
