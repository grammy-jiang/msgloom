"""A1 saved-source relationship contract for Teams chat messageReference."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from message_ingest.catalog.models.microsoft.teams import (
    TeamsMessageAttachmentObservation,
)
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources._teams_catalog import scope_digest
from tests.source_reader.test_teams_saved_source import (
    SOURCE,
    _adapter,
    _build_fixture,
    _evidence,
    _observation,
    _version,
)


def test_chat_message_reference_preserves_candidate_and_exact_saved_target(
    tmp_path: Path,
) -> None:
    """Expose the chat relation without inventing channel-reply topology."""
    fixture = _build_fixture(tmp_path)
    engine = create_engine(f"sqlite:///{fixture.database}")
    reply_at = "2026-10-04T00:00:04+00:00"
    attachment = {
        "id": "reply-reference",
        "contentType": "messageReference",
        "content": '{"messageId":"same-message"}',
    }
    raw = {
        "id": "chat-reply",
        "etag": "etag-chat-reply",
        "createdDateTime": reply_at,
        "lastModifiedDateTime": reply_at,
        "messageType": "message",
        "from": {"user": {"id": "user-b", "displayName": "Bob"}},
        "body": {"contentType": "html", "content": "reply"},
        "attachments": [attachment],
    }
    with Session(engine) as session, session.begin():
        _evidence(session, fixture.evidence_root, "chat-reply", raw, reply_at)
        session.add(
            _observation(
                5,
                "chat",
                ("chat-a", "chat-reply"),
                raw,
                reply_at,
                "chat-reply",
            )
        )
        session.add(
            TeamsMessageAttachmentObservation(
                message_observation_id=5,
                ordinal=0,
                source_id=SOURCE,
                scope_key_sha256=scope_digest(
                    ["message", "chat", "chat-a", "chat-reply"]
                ),
                attachment_id="reply-reference",
                kind="message-reference",
                content_type="messageReference",
                raw=attachment,
            )
        )
    engine.dispose()
    source = _version(
        PreparedSourceType.TEAMS_CHAT_MESSAGE,
        ("chat", "chat-a", "chat-reply"),
        5,
        "chat-reply",
    )
    with _adapter(fixture) as adapter:
        record = adapter.read(source)
    candidates = [
        relation
        for relation in record.relationships
        if relation.kind == "teams_chat_message_reference"
    ]
    exact = [
        relation
        for relation in record.relationships
        if relation.kind == "teams_chat_reply_to"
    ]
    if len(candidates) != 1 or candidates[0].target.identity != fixture.chat_a.identity:
        pytest.fail("Teams messageReference candidate identity was not preserved")
    if len(exact) != 1 or exact[0].target != fixture.chat_a:
        pytest.fail("Teams messageReference did not resolve the exact saved target")


def test_corrupt_reply_target_retains_candidate_without_confirmed_edge(
    tmp_path: Path,
) -> None:
    """A missing target capture cannot become a confirmed message relation."""
    fixture = _build_fixture(tmp_path)
    reply_at = "2026-10-04T00:00:04+00:00"
    attachment = {
        "id": "reference",
        "contentType": "messageReference",
        "content": '{"messageId":"same-message"}',
    }
    raw = {
        "id": "new-reply",
        "etag": "etag-new",
        "createdDateTime": reply_at,
        "lastModifiedDateTime": reply_at,
        "messageType": "message",
        "from": {"user": {"id": "user-b", "displayName": "Bob"}},
        "body": {"contentType": "html", "content": "hello"},
        "attachments": [attachment],
    }
    engine = create_engine(f"sqlite:///{fixture.database}")
    with Session(engine) as session, session.begin():
        _evidence(session, fixture.evidence_root, "new-reply-evidence", raw, reply_at)
        session.add(
            _observation(
                5, "chat", ("chat-a", "new-reply"), raw, reply_at, "new-reply-evidence"
            )
        )
        session.add(
            TeamsMessageAttachmentObservation(
                message_observation_id=5,
                ordinal=0,
                source_id=SOURCE,
                scope_key_sha256=scope_digest(
                    ["message", "chat", "chat-a", "new-reply"]
                ),
                attachment_id="reference",
                kind="message-reference",
                content_type="messageReference",
                raw=attachment,
            )
        )
    engine.dispose()
    # The referenced message is present in SQL but has lost its captured bytes.
    (fixture.evidence_root / "chat-a-v1.bin").unlink()
    source = _version(
        PreparedSourceType.TEAMS_CHAT_MESSAGE,
        ("chat", "chat-a", "new-reply"),
        5,
        "new-reply-evidence",
    )
    with _adapter(fixture) as adapter:
        record = adapter.read(source)
    candidates = [
        r for r in record.relationships if r.kind == "teams_chat_message_reference"
    ]
    verified = [r for r in record.relationships if r.kind == "teams_chat_reply_to"]
    if len(candidates) != 1 or verified:
        pytest.fail("Corrupt target was either lost or incorrectly confirmed")
    if not any(
        l.code == "teams-message-reference-target-unavailable"
        for l in record.limitations
    ):
        pytest.fail("Unverifiable reference lacks a safe limitation")
