"""Selection-snapshot tests for immutable Teams saved-source handoff."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from msgloom.preparation.records import PreparedSourceType
from msgloom.sources._snapshot import (
    capture_selection,
    decode_selection,
    encode_selection,
)
from tests.source_reader.test_teams_saved_history import _add_history
from tests.source_reader.test_teams_saved_source import (
    SOURCE,
    _adapter,
    _build_fixture,
    _evidence,
    _message,
    _observation,
    _TeamsFixture,
    _version,
)

EDIT_AT = "2026-10-04T00:20:00+00:00"
SNAPSHOT_LIMIT = 32 * 1024 * 1024


def _add_later_edit(fixture: _TeamsFixture) -> None:
    engine = create_engine(f"sqlite:///{fixture.database}")
    raw = _message(
        message_id="same-message",
        body="after edit",
        observed_at=EDIT_AT,
    )
    with Session(engine) as session, session.begin():
        _evidence(
            session,
            fixture.evidence_root,
            "chat-a-v2",
            raw,
            EDIT_AT,
        )
        session.add(
            _observation(
                5,
                "chat",
                ("chat-a", "same-message"),
                raw,
                EDIT_AT,
                "chat-a-v2",
            )
        )
    engine.dispose()


def test_captured_selection_replays_after_later_edit_and_history(
    tmp_path: Path,
) -> None:
    fixture = _build_fixture(tmp_path)
    with _adapter(fixture) as adapter:
        before_record = adapter.read(fixture.chat_a)
        before = capture_selection(before_record)
        encoded = encode_selection(before, SNAPSHOT_LIMIT)
    if before.record.source_bytes is None:
        pytest.fail("Initial Teams selection did not retain raw evidence")
    expected_digest = hashlib.sha256(
        (fixture.evidence_root / "chat-a-v1.bin").read_bytes()
    ).hexdigest()
    if before.record.source_bytes.sha256 != expected_digest:
        pytest.fail("Initial selection stored the wrong evidence hash")

    _add_history(fixture)
    _add_later_edit(fixture)

    replay = decode_selection(encoded, SNAPSHOT_LIMIT)
    if replay != before:
        pytest.fail("Persisted Teams selection drifted after catalog changes")
    if replay.record.body is None or replay.record.body.content != "before edit":
        pytest.fail("Replayed old selection changed its captured message body")

    with _adapter(fixture) as adapter:
        fresh = capture_selection(adapter.read(fixture.chat_a))
        refs = adapter.list_versions(
            PreparedSourceType.TEAMS_CHAT_MESSAGE,
            SOURCE,
            10,
        )
    if fresh.selection == before.selection:
        pytest.fail("Fresh component selection ignored later additive history")
    if fresh.record.body is None or fresh.record.body.content != "before edit":
        pytest.fail("Later observations rewrote the old primary message version")
    if fixture.chat_a not in refs:
        pytest.fail("Old scoped Teams version disappeared after a later edit")
    codes = {item.code for item in fresh.record.limitations}
    if "teams-explicit-deletion-observed" not in codes:
        pytest.fail("Fresh selection did not capture later deletion history")
    if "teams-history-incomplete" not in codes:
        pytest.fail("Fresh selection did not capture later coverage gap")


def test_later_edit_is_distinct_version_and_old_provenance_stays_exact(
    tmp_path: Path,
) -> None:
    fixture = _build_fixture(tmp_path)
    _add_later_edit(fixture)
    edited = _version(
        PreparedSourceType.TEAMS_CHAT_MESSAGE,
        ("chat", "chat-a", "same-message"),
        5,
        "chat-a-v2",
    )
    with _adapter(fixture) as adapter:
        old = adapter.read(fixture.chat_a)
        new = adapter.read(edited)
    if old.source == new.source:
        pytest.fail("Later edit reused the old immutable source version")
    if old.semantic_identity != new.semantic_identity:
        pytest.fail("Edits to one scoped message changed semantic identity")
    if old.body is None or old.body.content != "before edit":
        pytest.fail("Old saved version was rewritten by later edit")
    if new.body is None or new.body.content != "after edit":
        pytest.fail("Later edit did not map from its own evidence")
    if old.source_bytes is None or new.source_bytes is None:
        pytest.fail("Message versions lost their exact raw evidence references")
    if old.source_bytes.reference == new.source_bytes.reference:
        pytest.fail("Distinct captures reused one evidence reference")


def test_component_snapshot_versions_embed_exact_evidence_and_paths(
    tmp_path: Path,
) -> None:
    fixture = _build_fixture(tmp_path)
    _add_history(fixture)
    with _adapter(fixture) as adapter:
        selection = capture_selection(adapter.read(fixture.channel_reply))
    topology = [
        relation
        for relation in selection.record.relationships
        if relation.kind == "teams_topology"
    ]
    if not topology:
        pytest.fail("Topology component versions were not captured")
    decoded = [json.loads(relation.target.version) for relation in topology]
    membership = [
        value for value in decoded if value.get("resource_kind") == "channel-membership"
    ]
    if len(membership) != 2:
        pytest.fail("Snapshot lost one distinct membership path")
    if any(not value.get("evidence_id") for value in membership):
        pytest.fail("Topology snapshot omitted evidence provenance")
    scopes = {tuple(value["scope_key"]) for value in membership}
    if len(scopes) != 2:
        pytest.fail("Snapshot collapsed full topology paths")
