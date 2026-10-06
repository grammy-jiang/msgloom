"""Assert exact A1 release structure after a real local Graph crawl."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

GroupKey = tuple[str, str]
GroupExpectation = tuple[str, bool, int]
FactExpectation = tuple[str, str | None]
EntryExpectation = tuple[str, str, object, tuple[FactExpectation, ...]]


def _entry_signature(entry: EntryExpectation) -> tuple[object, ...]:
    """Return a sortable signature while preserving ordered fact membership."""
    entry_kind, resource_kind, resource_identity, facts = entry
    identity = json.dumps(
        resource_identity,
        sort_keys=True,
        separators=(",", ":"),
    )
    return entry_kind, resource_kind, identity, facts


def assert_release_contract(
    database: Path,
    *,
    source_id: str,
    stream: str,
    expected_groups: dict[GroupKey, GroupExpectation],
    expected_entries: dict[GroupKey, tuple[EntryExpectation, ...]],
    expected_fact_spiders: set[str],
) -> None:
    """Check exact groups, membership, fact ownership, and authority.

    ``expected_groups`` maps ``(subject_kind, subject_identity)`` to
    ``(release_kind, authoritative, entry_count)``. The caller owns
    provider-specific identities. ``expected_entries`` binds each group to
    exact entry identities and ordered ``(role, component_kind)`` facts.
    This helper owns the shared release-ledger structure and fails if any
    entry or fact falls outside its atomic group.
    """
    if set(expected_entries) != set(expected_groups):
        pytest.fail("Entry expectations do not cover the exact release groups")
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        groups = connection.execute(
            "SELECT release_group_id, source_id, stream, payload "
            "FROM acquisition_release_groups ORDER BY rowid"
        ).fetchall()
        if len(groups) != len(expected_groups):
            pytest.fail("Real crawl released an unexpected group count")

        actual_keys: set[GroupKey] = set()
        actual_spiders: set[str] = set()
        for group_row in groups:
            group = json.loads(group_row["payload"])
            key = (group["subject_kind"], group["subject_identity"])
            if key in actual_keys or key not in expected_groups:
                pytest.fail("Real crawl released an unexpected or duplicate subject")
            actual_keys.add(key)
            release_kind, authoritative, entry_count = expected_groups[key]
            owner_run_id = group["owner_run_id"]
            if (
                group_row["source_id"] != source_id
                or group_row["stream"] != stream
                or group["source_id"] != source_id
                or group["stream"] != stream
                or group["release_kind"] != release_kind
                or group["coverage_kind"] != "complete"
            ):
                pytest.fail("Release group lost its exact stream or semantics")
            revision = group["authority_revision"]
            if authoritative and revision != owner_run_id:
                pytest.fail("Authority group was not committed by its owner run")
            if not authoritative and revision is not None:
                pytest.fail("Additive release acquired absence authority")

            entries = connection.execute(
                "SELECT release_entry_seq, source_id, stream, payload "
                "FROM acquisition_release_entries WHERE release_group_id = ? "
                "ORDER BY release_entry_seq",
                (group_row["release_group_id"],),
            ).fetchall()
            if len(entries) != entry_count:
                pytest.fail("Release subject has the wrong exact entry count")
            actual_entries: list[EntryExpectation] = []
            for entry_row in entries:
                entry = json.loads(entry_row["payload"])
                if (
                    entry_row["source_id"] != source_id
                    or entry_row["stream"] != stream
                    or not entry["facts"]
                ):
                    pytest.fail("Release entry lost its stream or fact membership")
                members = connection.execute(
                    "SELECT fact_id, role FROM acquisition_release_entry_facts "
                    "WHERE release_entry_seq = ? ORDER BY ordinal",
                    (entry_row["release_entry_seq"],),
                ).fetchall()
                if [[row["fact_id"], row["role"]] for row in members] != entry["facts"]:
                    pytest.fail("Entry payload differs from ordered fact membership")
                actual_members: list[FactExpectation] = []
                for member in members:
                    fact_row = connection.execute(
                        "SELECT source_id, stream, run_id, source_state_key, payload "
                        "FROM acquisition_facts WHERE fact_id = ?",
                        (member["fact_id"],),
                    ).fetchone()
                    if fact_row is None:
                        pytest.fail("Release membership cites a missing fact")
                        continue
                    fact = json.loads(fact_row["payload"])
                    state_key = fact["source_state_key"]
                    if (
                        fact_row["source_id"] != source_id
                        or fact_row["stream"] != stream
                        or fact_row["run_id"] != fact["run_id"]
                        or (authoritative and fact_row["run_id"] != owner_run_id)
                        or fact_row["source_state_key"] != state_key
                        or not isinstance(state_key, str)
                        or len(state_key) != 64
                        or any(
                            character not in "0123456789abcdef"
                            for character in state_key
                        )
                    ):
                        pytest.fail("Released fact lost source-state or run ownership")
                    actual_members.append((member["role"], fact["component_kind"]))
                    actual_spiders.add(fact["spider_name"])
                actual_entries.append(
                    (
                        entry["entry_kind"],
                        entry["resource_kind"],
                        entry["resource_identity"],
                        tuple(actual_members),
                    )
                )
            actual_signatures = sorted(map(_entry_signature, actual_entries))
            expected_signatures = sorted(map(_entry_signature, expected_entries[key]))
            if actual_signatures != expected_signatures:
                pytest.fail("Release subject lost exact entry or fact membership")

    if actual_keys != set(expected_groups):
        pytest.fail("Real crawl did not release every expected subject")
    if actual_spiders != expected_fact_spiders:
        pytest.fail("Release facts do not bind the exact mapped spiders")
