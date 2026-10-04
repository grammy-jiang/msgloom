"""Saved-source tests for exact Teams message identity and evidence."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from message_ingest.catalog.models import Base
from message_ingest.catalog.models.acquisition import RawHttpEvidence, SourceBinding
from message_ingest.catalog.models.microsoft.teams import (
    TeamsMessageAttachmentObservation,
    TeamsMessageObservation,
)
from msgloom.contracts import VersionRef
from msgloom.preparation.records import PreparedSourceType
from msgloom.sources._catalog import ReadOnlyCatalog, encode_parts
from msgloom.sources._io import EvidenceFiles
from msgloom.sources._teams import TeamsSavedSourceAdapter
from msgloom.sources._teams_catalog import scope_digest
from msgloom.sources.models import (
    SourceEvidenceError,
    SourceReaderLimits,
    SourceReferenceError,
)

SOURCE = "synthetic-teams-source"
OLD_AT = "2026-10-04T00:00:00+00:00"
RUN = "teams-test-run"


@dataclass(frozen=True, slots=True)
class _TeamsFixture:
    database: Path
    evidence_root: Path
    chat_a: VersionRef
    chat_b: VersionRef
    channel_root: VersionRef
    channel_reply: VersionRef


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def _evidence(
    session: Session,
    root: Path,
    evidence_id: str,
    body: object,
    observed_at: str,
    *,
    source_id: str = SOURCE,
    purpose: str = "teams-test",
) -> RawHttpEvidence:
    data = body if isinstance(body, bytes) else _json_bytes(body)
    path = root / f"{evidence_id}.bin"
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    row = RawHttpEvidence(
        evidence_id=evidence_id,
        source_id=source_id,
        run_id=RUN,
        purpose=purpose,
        observed_at=observed_at,
        origin="network",
        request_fingerprint=hashlib.sha256(evidence_id.encode()).hexdigest(),
        request_url="https://graph.example.invalid/v1.0/teams-test",
        request_method="GET",
        request_headers={},
        request_body_sha256=hashlib.sha256(b"").hexdigest(),
        request_body_path=str(root / "empty.bin"),
        request_body_bytes=0,
        response_url="https://graph.example.invalid/v1.0/teams-test",
        response_status=200,
        response_headers={"content-type": ["application/json"]},
        response_body_sha256=digest,
        response_body_path=str(path),
        response_body_bytes=len(data),
        response_flags=[],
        error_type=None,
        error_message=None,
    )
    session.add(row)
    return row


def _message(
    *,
    message_id: str,
    body: str,
    observed_at: str,
    attachments: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": message_id,
        "etag": f"etag-{observed_at}",
        "createdDateTime": "2026-10-03T23:59:00Z",
        "lastModifiedDateTime": observed_at,
        "messageType": "message",
        "importance": "normal",
        "from": {"user": {"id": "user-a", "displayName": "Alice"}},
        "body": {"contentType": "html", "content": body},
        "attachments": attachments or [],
    }


def _version(
    kind: PreparedSourceType,
    identity: tuple[str, ...],
    observation_id: int,
    evidence_id: str,
) -> VersionRef:
    return VersionRef(
        kind.value,
        encode_parts(SOURCE, *identity),
        encode_parts(str(observation_id), evidence_id),
    )


def _observation(
    observation_id: int,
    location: str,
    identity: tuple[str, ...],
    raw: dict[str, object],
    observed_at: str,
    evidence_id: str,
) -> TeamsMessageObservation:
    if location == "chat":
        chat_id, message_id = identity
        team_id = channel_id = root_message_id = None
    elif location == "channel-root":
        team_id, channel_id, message_id = identity
        chat_id = root_message_id = None
    else:
        team_id, channel_id, root_message_id, message_id = identity
        chat_id = None
    scope = ["message", location, *identity]
    return TeamsMessageObservation(
        observation_id=observation_id,
        source_id=SOURCE,
        scope_key=scope,
        scope_key_sha256=scope_digest(scope),
        location=location,
        message_id=message_id,
        chat_id=chat_id,
        team_id=team_id,
        channel_id=channel_id,
        root_message_id=root_message_id,
        provider_etag=raw.get("etag"),
        deleted_date_time=None,
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id=RUN,
        evidence_run_id=RUN,
        raw=raw,
    )


def _build_fixture(tmp_path: Path) -> _TeamsFixture:
    database = tmp_path / "catalog.sqlite3"
    root = tmp_path / "evidence"
    root.mkdir(parents=True)
    (root / "empty.bin").write_bytes(b"")
    engine = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(engine)
    reference: dict[str, object] = {
        "id": "reference-1",
        "contentType": "reference",
        "contentUrl": "https://sharepoint.example.invalid/not-fetched",
        "name": "report.docx",
    }
    chat_a = _message(
        message_id="same-message",
        body="before edit",
        observed_at=OLD_AT,
        attachments=[reference],
    )
    chat_b_at = "2026-10-04T00:00:01+00:00"
    chat_b = _message(
        message_id="same-message",
        body="other chat",
        observed_at=chat_b_at,
    )
    root_at = "2026-10-04T00:00:02+00:00"
    root_raw = _message(
        message_id="root-1",
        body="channel root",
        observed_at=root_at,
    )
    reply_at = "2026-10-04T00:00:03+00:00"
    reply_raw = _message(
        message_id="reply-1",
        body="channel reply",
        observed_at=reply_at,
    )
    with Session(engine) as session, session.begin():
        session.add(
            SourceBinding(
                source_id=SOURCE,
                provider="microsoft",
                key_scheme="teams-test",
                account_key_sha256="a" * 64,
                binding_method="test",
                bound_at="2026-10-04T00:00:00+00:00",
            )
        )
        for evidence_id, raw, observed_at in (
            ("chat-a-v1", chat_a, OLD_AT),
            ("chat-b-v1", chat_b, chat_b_at),
            ("channel-root", root_raw, root_at),
            ("channel-reply", reply_raw, reply_at),
        ):
            _evidence(session, root, evidence_id, raw, observed_at)
        session.add_all(
            [
                _observation(
                    1, "chat", ("chat-a", "same-message"), chat_a, OLD_AT, "chat-a-v1"
                ),
                _observation(
                    2,
                    "chat",
                    ("chat-b", "same-message"),
                    chat_b,
                    chat_b_at,
                    "chat-b-v1",
                ),
                _observation(
                    3,
                    "channel-root",
                    ("team-a", "channel-a", "root-1"),
                    root_raw,
                    root_at,
                    "channel-root",
                ),
                _observation(
                    4,
                    "channel-reply",
                    ("team-a", "channel-a", "root-1", "reply-1"),
                    reply_raw,
                    reply_at,
                    "channel-reply",
                ),
                TeamsMessageAttachmentObservation(
                    message_observation_id=1,
                    ordinal=0,
                    source_id=SOURCE,
                    scope_key_sha256=scope_digest(
                        ["message", "chat", "chat-a", "same-message"]
                    ),
                    attachment_id="reference-1",
                    kind="reference",
                    content_type="reference",
                    raw=reference,
                ),
            ]
        )
    engine.dispose()
    return _TeamsFixture(
        database=database,
        evidence_root=root,
        chat_a=_version(
            PreparedSourceType.TEAMS_CHAT_MESSAGE,
            ("chat", "chat-a", "same-message"),
            1,
            "chat-a-v1",
        ),
        chat_b=_version(
            PreparedSourceType.TEAMS_CHAT_MESSAGE,
            ("chat", "chat-b", "same-message"),
            2,
            "chat-b-v1",
        ),
        channel_root=_version(
            PreparedSourceType.TEAMS_CHANNEL_MESSAGE,
            ("channel-root", "team-a", "channel-a", "root-1"),
            3,
            "channel-root",
        ),
        channel_reply=_version(
            PreparedSourceType.TEAMS_CHANNEL_MESSAGE,
            ("channel-reply", "team-a", "channel-a", "root-1", "reply-1"),
            4,
            "channel-reply",
        ),
    )


@contextmanager
def _adapter(
    fixture: _TeamsFixture,
    limits: SourceReaderLimits | None = None,
) -> Iterator[TeamsSavedSourceAdapter]:
    configured = limits or SourceReaderLimits()
    catalog = ReadOnlyCatalog(fixture.database, configured)
    files = EvidenceFiles((fixture.evidence_root,), configured.max_evidence_bytes)
    try:
        yield TeamsSavedSourceAdapter(catalog, files)
    finally:
        files.close()
        catalog.close()


def test_scoped_duplicate_ids_list_and_read_exact_evidence(tmp_path: Path) -> None:
    fixture = _build_fixture(tmp_path)
    with _adapter(fixture) as adapter:
        refs = adapter.list_versions(
            PreparedSourceType.TEAMS_CHAT_MESSAGE,
            SOURCE,
            10,
        )
        if set(refs) != {fixture.chat_a, fixture.chat_b}:
            pytest.fail("Duplicate message IDs in distinct chats were collapsed")
        first = adapter.read(fixture.chat_a)
        second = adapter.read(fixture.chat_b)
        if first.semantic_identity == second.semantic_identity:
            pytest.fail("Scoped Teams message identities collided")
        if first.body is None or first.body.content != "before edit":
            pytest.fail("Exact old chat evidence was not mapped")
        if first.source_bytes is None:
            pytest.fail("Primary Teams raw evidence reference was not retained")
        if first.author is None or first.author.identity != "user:user-a":
            pytest.fail("Teams sender identity was not preserved")
        if len(first.attachments) != 1:
            pytest.fail("Embedded attachment taxonomy was not retained")


@pytest.mark.parametrize(
    "replacement",
    (
        VersionRef(
            PreparedSourceType.TEAMS_CHAT_MESSAGE.value,
            encode_parts(SOURCE, "chat", "chat-a", "same-message"),
            "01/chat-a-v1",
        ),
        VersionRef(
            PreparedSourceType.TEAMS_CHAT_MESSAGE.value,
            encode_parts(SOURCE, "chat", "chat-z", "same-message"),
            "1/chat-a-v1",
        ),
    ),
)
def test_invalid_version_or_scope_fails_closed(
    tmp_path: Path,
    replacement: VersionRef,
) -> None:
    fixture = _build_fixture(tmp_path)
    with _adapter(fixture) as adapter, pytest.raises(SourceReferenceError):
        adapter.read(replacement)


def test_wrong_source_hash_and_path_evidence_fail_closed(tmp_path: Path) -> None:
    fixture = _build_fixture(tmp_path)
    with sqlite3.connect(fixture.database) as connection:
        connection.execute(
            "UPDATE raw_http_evidence SET source_id = ? WHERE evidence_id = ?",
            ("other-source", "chat-a-v1"),
        )
    with (
        _adapter(fixture) as adapter,
        pytest.raises(SourceEvidenceError, match="another source"),
    ):
        adapter.read(fixture.chat_a)

    fixture = _build_fixture(tmp_path / "hash")
    (fixture.evidence_root / "chat-a-v1.bin").write_bytes(b"tampered")
    with (
        _adapter(fixture) as adapter,
        pytest.raises(SourceEvidenceError, match="digest|byte count"),
    ):
        adapter.read(fixture.chat_a)

    fixture = _build_fixture(tmp_path / "escape")
    original = fixture.evidence_root / "chat-a-v1.bin"
    outside = fixture.evidence_root.parent / "outside.bin"
    outside.write_bytes(original.read_bytes())
    with sqlite3.connect(fixture.database) as connection:
        connection.execute(
            "UPDATE raw_http_evidence SET response_body_path = ? WHERE evidence_id = ?",
            (str(outside), "chat-a-v1"),
        )
    with (
        _adapter(fixture) as adapter,
        pytest.raises(SourceEvidenceError, match="escapes configured roots"),
    ):
        adapter.read(fixture.chat_a)
