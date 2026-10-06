"""Regression tests for real-crawl release assertions."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from tests.handoff_qualification.release_assertions import (
    assert_release_contract,
)


def test_release_contract_rejects_missing_required_mime(tmp_path: Path) -> None:
    """Reject an entry when both stored memberships omit required MIME."""
    database = tmp_path / "catalog.sqlite3"
    group_id = "group-one"
    primary_id = "primary-fact"
    mime_id = "mime-fact"
    group = {
        "subject_kind": "message",
        "subject_identity": "message-one",
        "owner_run_id": "run-one",
        "source_id": "mail-fixture",
        "stream": "outlook_mail",
        "release_kind": "resource_profile",
        "coverage_kind": "complete",
        "authority_revision": None,
    }
    entry = {
        "entry_kind": "resource",
        "resource_kind": "message",
        "resource_identity": "message-one",
        "facts": [
            [primary_id, "primary"],
            [mime_id, "component"],
        ],
    }
    fact = {
        "run_id": "run-one",
        "source_state_key": "a" * 64,
        "spider_name": "outlook_full",
        "component_kind": None,
    }
    mime_fact = {**fact, "component_kind": "mime"}
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE acquisition_release_groups (
                release_group_id TEXT, source_id TEXT, stream TEXT, payload TEXT
            );
            CREATE TABLE acquisition_release_entries (
                release_entry_seq INTEGER, release_group_id TEXT,
                source_id TEXT, stream TEXT, payload TEXT
            );
            CREATE TABLE acquisition_release_entry_facts (
                release_entry_seq INTEGER, ordinal INTEGER,
                fact_id TEXT, role TEXT
            );
            CREATE TABLE acquisition_facts (
                fact_id TEXT, source_id TEXT, stream TEXT, run_id TEXT,
                source_state_key TEXT, payload TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO acquisition_release_groups VALUES (?, ?, ?, ?)",
            (group_id, "mail-fixture", "outlook_mail", json.dumps(group)),
        )
        connection.execute(
            "INSERT INTO acquisition_release_entries VALUES (?, ?, ?, ?, ?)",
            (1, group_id, "mail-fixture", "outlook_mail", json.dumps(entry)),
        )
        connection.execute(
            "INSERT INTO acquisition_release_entry_facts VALUES (?, ?, ?, ?)",
            (1, 0, primary_id, "primary"),
        )
        connection.execute(
            "INSERT INTO acquisition_release_entry_facts VALUES (?, ?, ?, ?)",
            (1, 1, mime_id, "component"),
        )
        connection.execute(
            "INSERT INTO acquisition_facts VALUES (?, ?, ?, ?, ?, ?)",
            (
                primary_id,
                "mail-fixture",
                "outlook_mail",
                "run-one",
                "a" * 64,
                json.dumps(fact),
            ),
        )
        connection.execute(
            "INSERT INTO acquisition_facts VALUES (?, ?, ?, ?, ?, ?)",
            (
                mime_id,
                "mail-fixture",
                "outlook_mail",
                "run-one",
                "a" * 64,
                json.dumps(mime_fact),
            ),
        )

    def check_release() -> None:
        assert_release_contract(
            database,
            source_id="mail-fixture",
            stream="outlook_mail",
            expected_groups={
                ("message", "message-one"): ("resource_profile", False, 1),
            },
            expected_entries={
                ("message", "message-one"): (
                    (
                        "resource",
                        "message",
                        "message-one",
                        (
                            ("primary", None),
                            ("component", "mime"),
                        ),
                    ),
                ),
            },
            expected_fact_spiders={"outlook_full"},
        )

    check_release()
    entry["facts"] = [[primary_id, "primary"]]
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE acquisition_release_entries SET payload = ?",
            (json.dumps(entry),),
        )
        connection.execute(
            "DELETE FROM acquisition_release_entry_facts WHERE fact_id = ?",
            (mime_id,),
        )

    with pytest.raises(
        pytest.fail.Exception,
        match="exact entry or fact membership",
    ):
        check_release()
