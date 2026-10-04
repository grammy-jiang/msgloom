"""Prevent saved coverage from crossing Teams resource kinds with equal IDs."""

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tests.source_reader.test_teams_saved_history import _coverage
from tests.source_reader.test_teams_saved_source import (
    OLD_AT,
    _adapter,
    _build_fixture,
    _evidence,
)


@pytest.mark.parametrize(
    ("selected_name", "matching_kind", "matching_scope", "other_kind", "other_scope"),
    [
        (
            "chat_a",
            "chat-messages",
            ("chat-a",),
            "channel-messages",
            ("chat-a", "different-channel"),
        ),
        (
            "channel_root",
            "channel-messages",
            ("team-a", "channel-a"),
            "chat-messages",
            ("team-a",),
        ),
        (
            "channel_reply",
            "channel-messages",
            ("team-a", "channel-a"),
            "chat-messages",
            ("team-a",),
        ),
    ],
)
def test_saved_coverage_matches_resource_kind_and_opaque_scope(
    tmp_path: Path,
    selected_name: str,
    matching_kind: str,
    matching_scope: tuple[str, ...],
    other_kind: str,
    other_scope: tuple[str, ...],
) -> None:
    """Same raw IDs cannot make another resource's delivery gap applicable."""
    fixture = _build_fixture(tmp_path)
    engine = create_engine(f"sqlite:///{fixture.database}")
    try:
        with Session(engine) as session, session.begin():
            for number, (kind, scope, evidence_id) in enumerate(
                (
                    (matching_kind, matching_scope, "matching-gap"),
                    (other_kind, other_scope, "unrelated-gap"),
                ),
                start=900,
            ):
                _evidence(session, fixture.evidence_root, evidence_id, {}, OLD_AT)
                session.add(
                    _coverage(
                        number,
                        kind,
                        ["coverage", kind, *scope],
                        OLD_AT,
                        evidence_id,
                        history_incomplete=True,
                        fact_kind="gap",
                        status="unknown",
                        gap_kind="subscription-removed",
                    )
                )
    finally:
        engine.dispose()
    with _adapter(fixture) as adapter:
        record = adapter.read(getattr(fixture, selected_name))
    facts = [
        json.loads(relation.target.version)
        for relation in record.relationships
        if relation.kind == "teams_coverage"
    ]
    if {fact["evidence_id"] for fact in facts} != {"matching-gap"}:
        pytest.fail("Saved coverage crossed resource kinds or lost the matching gap")
