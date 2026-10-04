"""History-preservation tests for the Teams saved-source adapter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from message_ingest.catalog.models.microsoft.teams import (
    TeamsCoverageObservation,
    TeamsHostedContentObservation,
    TeamsMessageDeletionObservation,
    TeamsReferenceResolutionObservation,
    TeamsTopologyObservation,
)
from msgloom.sources._teams_catalog import scope_digest
from msgloom.sources.models import SourceReaderLimits, SourceReferenceError
from tests.source_reader.test_teams_saved_source import (
    OLD_AT,
    RUN,
    SOURCE,
    _adapter,
    _build_fixture,
    _evidence,
    _TeamsFixture,
)


def _topology(
    observation_id: int,
    resource_kind: str,
    scope: list[str],
    observed_at: str,
    evidence_id: str,
    raw: dict[str, object] | None,
    context: dict[str, object],
) -> TeamsTopologyObservation:
    return TeamsTopologyObservation(
        observation_id=observation_id,
        source_id=SOURCE,
        resource_kind=resource_kind,
        scope_key=scope,
        scope_key_sha256=scope_digest(scope),
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id=RUN,
        evidence_run_id=RUN,
        raw=raw,
        context=context,
    )


def _coverage(
    observation_id: int,
    scope_kind: str,
    scope: list[str],
    observed_at: str,
    evidence_id: str,
    *,
    history_incomplete: bool,
    fact_kind: str,
    status: str,
    gap_kind: str | None,
) -> TeamsCoverageObservation:
    return TeamsCoverageObservation(
        observation_id=observation_id,
        source_id=SOURCE,
        scope_kind=scope_kind,
        scope_key=scope,
        scope_key_sha256=scope_digest(scope),
        fact_kind=fact_kind,
        status=status,
        history_incomplete=history_incomplete,
        visible_scope={"scope": scope[2:]},
        retention_limitations=["provider-visible retained history only"],
        subscription_id="subscription-a",
        subscription_valid_from="2026-10-04T00:00:00+00:00",
        subscription_valid_until=(
            "2026-10-04T00:10:00+00:00" if history_incomplete else None
        ),
        gap_kind=gap_kind,
        details={"fact": fact_kind},
        observed_at=observed_at,
        evidence_id=evidence_id,
        run_id=RUN,
        evidence_run_id=RUN,
    )


def _add_history(fixture: _TeamsFixture) -> None:
    engine = create_engine(f"sqlite:///{fixture.database}")
    chat_scope = ["message", "chat", "chat-a", "same-message"]
    chat_digest = scope_digest(chat_scope)
    with Session(engine) as session, session.begin():
        evidence = (
            ("ref-denied", {"error": "forbidden"}, "2026-10-04T00:04:00+00:00"),
            ("delete", {"changeType": "deleted"}, "2026-10-04T00:05:00+00:00"),
            ("delete-readback", {"status": 410}, "2026-10-04T00:06:00+00:00"),
            ("hosted-meta", {"id": "host-1"}, "2026-10-04T00:07:00+00:00"),
            ("hosted-failure", {"status": 410}, "2026-10-04T00:09:00+00:00"),
            ("top-chat", {"id": "chat-a"}, "2026-10-04T00:02:00+00:00"),
            ("top-member", {"id": "member-a"}, "2026-10-04T00:02:01+00:00"),
            ("top-pin", {"id": "same-message"}, "2026-10-04T00:02:02+00:00"),
            ("top-team", {"id": "team-a"}, "2026-10-04T00:02:03+00:00"),
            ("top-channel", {"id": "channel-a"}, "2026-10-04T00:02:04+00:00"),
            ("top-member-1", {"id": "membership"}, "2026-10-04T00:02:05+00:00"),
            ("top-member-2", {"id": "membership"}, "2026-10-04T00:02:06+00:00"),
            ("gap-chat", {"gap": True}, "2026-10-04T00:10:00+00:00"),
            ("reconcile-chat", {"read": True}, "2026-10-04T00:11:00+00:00"),
            ("gap-channel", {"gap": True}, "2026-10-04T00:12:00+00:00"),
        )
        for evidence_id, body, observed_at in evidence:
            _evidence(session, fixture.evidence_root, evidence_id, body, observed_at)
        hosted_bytes = b"PNG"
        _evidence(
            session,
            fixture.evidence_root,
            "hosted-bytes",
            hosted_bytes,
            "2026-10-04T00:08:00+00:00",
            purpose="teams-hosted-bytes",
        )
        session.add_all(
            [
                TeamsReferenceResolutionObservation(
                    observation_id=1,
                    source_id=SOURCE,
                    trigger_scope_sha256=chat_digest,
                    trigger_evidence_id="chat-a-v1",
                    trigger_observed_at=OLD_AT,
                    attachment_ordinal=0,
                    state="not-attempted",
                    observed_at=OLD_AT,
                    evidence_id="chat-a-v1",
                    run_id=RUN,
                    evidence_run_id=RUN,
                    details={"profile": "core-unselected"},
                ),
                TeamsReferenceResolutionObservation(
                    observation_id=2,
                    source_id=SOURCE,
                    trigger_scope_sha256=chat_digest,
                    trigger_evidence_id="chat-a-v1",
                    trigger_observed_at=OLD_AT,
                    attachment_ordinal=0,
                    state="denied",
                    observed_at="2026-10-04T00:04:00+00:00",
                    evidence_id="ref-denied",
                    run_id=RUN,
                    evidence_run_id=RUN,
                    details={"provider_status": 403},
                ),
                TeamsMessageDeletionObservation(
                    deletion_id=1,
                    source_id=SOURCE,
                    scope_key=chat_scope,
                    scope_key_sha256=chat_digest,
                    deletion_kind="notification",
                    declared_deleted_at="2026-10-04T00:05:00Z",
                    observed_at="2026-10-04T00:05:00+00:00",
                    evidence_id="delete",
                    run_id=RUN,
                    evidence_run_id=RUN,
                    readback_state="failed",
                    readback_observed_at="2026-10-04T00:06:00+00:00",
                    readback_evidence_id="delete-readback",
                    readback_evidence_run_id=RUN,
                ),
                TeamsHostedContentObservation(
                    observation_id=1,
                    source_id=SOURCE,
                    trigger_scope_sha256=chat_digest,
                    trigger_evidence_id="chat-a-v1",
                    trigger_observed_at=OLD_AT,
                    hosted_content_id="host-1",
                    observation_kind="metadata",
                    provider_version_bound=False,
                    observed_at="2026-10-04T00:07:00+00:00",
                    evidence_id="hosted-meta",
                    run_id=RUN,
                    evidence_run_id=RUN,
                    content_type="image/png",
                    content_sha256=None,
                    content_bytes=None,
                    failure_kind=None,
                    status_code=None,
                    raw={"id": "host-1", "contentType": "image/png"},
                    details={},
                ),
                TeamsHostedContentObservation(
                    observation_id=2,
                    source_id=SOURCE,
                    trigger_scope_sha256=chat_digest,
                    trigger_evidence_id="chat-a-v1",
                    trigger_observed_at=OLD_AT,
                    hosted_content_id="host-1",
                    observation_kind="bytes",
                    provider_version_bound=False,
                    observed_at="2026-10-04T00:08:00+00:00",
                    evidence_id="hosted-bytes",
                    run_id=RUN,
                    evidence_run_id=RUN,
                    content_type="image/png",
                    content_sha256=hashlib.sha256(hosted_bytes).hexdigest(),
                    content_bytes=len(hosted_bytes),
                    failure_kind=None,
                    status_code=None,
                    raw=None,
                    details={},
                ),
                TeamsHostedContentObservation(
                    observation_id=3,
                    source_id=SOURCE,
                    trigger_scope_sha256=chat_digest,
                    trigger_evidence_id="chat-a-v1",
                    trigger_observed_at=OLD_AT,
                    hosted_content_id="host-2",
                    observation_kind="failure",
                    provider_version_bound=False,
                    observed_at="2026-10-04T00:09:00+00:00",
                    evidence_id="hosted-failure",
                    run_id=RUN,
                    evidence_run_id=RUN,
                    content_type=None,
                    content_sha256=None,
                    content_bytes=None,
                    failure_kind="deleted-thread",
                    status_code=410,
                    raw=None,
                    details={"provider_limitation": "deleted thread"},
                ),
            ]
        )
        topology = [
            _topology(
                1,
                "chat",
                ["chat", "chat-a"],
                "2026-10-04T00:02:00+00:00",
                "top-chat",
                {"id": "chat-a"},
                {"chat_id": "chat-a", "chat_type": "group"},
            ),
            _topology(
                2,
                "chat-member",
                ["chat-member", "chat-a", "member-a"],
                "2026-10-04T00:02:01+00:00",
                "top-member",
                {"id": "member-a"},
                {"chat_id": "chat-a", "member_id": "member-a", "user_id": "user-a"},
            ),
            _topology(
                3,
                "pin",
                ["pin", "chat-a", "same-message"],
                "2026-10-04T00:02:02+00:00",
                "top-pin",
                {"id": "same-message"},
                {"chat_id": "chat-a", "message_id": "same-message", "state": "pinned"},
            ),
            _topology(
                4,
                "team",
                ["team", "team-a"],
                "2026-10-04T00:02:03+00:00",
                "top-team",
                {"id": "team-a"},
                {"team_id": "team-a", "representation": "associated"},
            ),
            _topology(
                5,
                "channel",
                ["channel", "team-a", "channel-a", "receiving-a"],
                "2026-10-04T00:02:04+00:00",
                "top-channel",
                {"id": "channel-a"},
                {
                    "channel_id": "channel-a",
                    "host_team_id": "team-a",
                    "receiving_team_id": "receiving-a",
                    "detail_complete": False,
                    "detail_limitation": "detail GET denied",
                    "original_resource_link": "https://graph.example.invalid/raw-link",
                },
            ),
        ]
        for ordinal in (1, 2):
            url = f"https://graph.example.invalid/source/{ordinal}"
            topology.append(
                _topology(
                    5 + ordinal,
                    "channel-membership",
                    [
                        "channel-membership",
                        "team-a",
                        "channel-a",
                        "allMembers",
                        "membership",
                        url,
                    ],
                    f"2026-10-04T00:02:0{4 + ordinal}+00:00",
                    f"top-member-{ordinal}",
                    {"id": "membership"},
                    {
                        "host_team_id": "team-a",
                        "channel_id": "channel-a",
                        "membership_id": "membership",
                        "membership_source": "allMembers",
                        "original_source_membership_url": url,
                    },
                )
            )
        session.add_all(topology)
        chat_coverage = ["coverage", "chat-messages", "chat-a"]
        channel_coverage = ["coverage", "channel-messages", "team-a", "channel-a"]
        session.add_all(
            [
                _coverage(
                    1,
                    "chat-messages",
                    chat_coverage,
                    "2026-10-04T00:10:00+00:00",
                    "gap-chat",
                    history_incomplete=True,
                    fact_kind="subscription-lifecycle",
                    status="gap",
                    gap_kind="subscription-removed",
                ),
                _coverage(
                    2,
                    "chat-messages",
                    chat_coverage,
                    "2026-10-04T00:11:00+00:00",
                    "reconcile-chat",
                    history_incomplete=False,
                    fact_kind="reconciliation",
                    status="current-state-read",
                    gap_kind=None,
                ),
                _coverage(
                    3,
                    "channel-messages",
                    channel_coverage,
                    "2026-10-04T00:12:00+00:00",
                    "gap-channel",
                    history_incomplete=True,
                    fact_kind="retention-window",
                    status="gap",
                    gap_kind="retention-boundary",
                ),
            ]
        )
    engine.dispose()


def _versions(record, kind: str) -> list[dict[str, object]]:
    values = []
    for relation in record.relationships:
        if relation.kind == kind:
            values.append(json.loads(relation.target.version))
    return values


def test_chat_history_preserves_reference_hosted_deletion_and_gap(
    tmp_path: Path,
) -> None:
    fixture = _build_fixture(tmp_path)
    _add_history(fixture)
    with _adapter(fixture) as adapter:
        record = adapter.read(fixture.chat_a)
    kinds = {relation.kind for relation in record.relationships}
    expected = {
        "teams_message_deletion",
        "teams_reference_resolution",
        "teams_hosted_content",
        "teams_topology",
        "teams_coverage",
    }
    if not expected <= kinds:
        pytest.fail(f"Teams history relations are incomplete: {kinds!r}")
    if record.body is None or record.body.content != "before edit":
        pytest.fail("Deletion history replaced an older captured message body")
    if not record.attachments:
        pytest.fail("Reference attachment was not preserved")
    reference_codes = {item.code for item in record.attachments[0].limitations}
    if (
        not {"teams-reference-not-attempted", "teams-reference-denied"}
        <= reference_codes
    ):
        pytest.fail("Reference non-fetch and denial states were not preserved")
    if record.attachments[0].saved_bytes is not None:
        pytest.fail("File reference was incorrectly treated as fetched content")
    hosted = [item for item in record.attachments if item.saved_bytes is not None]
    if len(hosted) != 1 or hosted[0].byte_count != 3:
        pytest.fail("Verified hosted bytes were not exposed exactly once")
    codes = {item.code for item in record.limitations}
    required = {
        "teams-explicit-deletion-observed",
        "teams-hosted-content-failure",
        "teams-history-incomplete",
        "teams-retention-limitation",
    }
    if not required <= codes:
        pytest.fail(f"History limitation facts were lost: {codes!r}")
    deletions = _versions(record, "teams_message_deletion")
    if deletions[0]["readback_evidence_id"] != "delete-readback":
        pytest.fail("Deletion readback provenance was not retained")
    coverage = _versions(record, "teams_coverage")
    if not any(value.get("gap_kind") == "subscription-removed" for value in coverage):
        pytest.fail("Coverage gap kind was not retained")


def test_channel_reply_preserves_root_and_distinct_membership_paths(
    tmp_path: Path,
) -> None:
    fixture = _build_fixture(tmp_path)
    _add_history(fixture)
    with _adapter(fixture) as adapter:
        record = adapter.read(fixture.channel_reply)
    reply = [
        relation
        for relation in record.relationships
        if relation.kind == "teams_channel_reply_to"
    ]
    if len(reply) != 1 or reply[0].target != fixture.channel_root:
        pytest.fail("Channel reply did not retain its exact saved root version")
    topology = _versions(record, "teams_topology")
    membership_scopes: list[list[object]] = []
    for value in topology:
        scope = value.get("scope_key")
        if value.get("resource_kind") == "channel-membership" and isinstance(
            scope, list
        ):
            membership_scopes.append(scope)
    if len(membership_scopes) != 2 or membership_scopes[0] == membership_scopes[1]:
        pytest.fail("Distinct allMembers topology paths were collapsed")
    urls = {scope[-1] for scope in membership_scopes}
    if urls != {
        "https://graph.example.invalid/source/1",
        "https://graph.example.invalid/source/2",
    }:
        pytest.fail("Original membership source paths were not preserved")
    if "teams-topology-detail-incomplete" not in {
        item.code for item in record.limitations
    }:
        pytest.fail("Inaccessible channel detail was not exposed as a limitation")


def test_component_queries_fail_closed_at_configured_row_bound(tmp_path: Path) -> None:
    fixture = _build_fixture(tmp_path)
    _add_history(fixture)
    limits = SourceReaderLimits(max_query_rows=1)
    with (
        _adapter(fixture, limits) as adapter,
        pytest.raises(
            SourceReferenceError,
            match="reference resolution inventory exceeds configured query bound",
        ),
    ):
        adapter.read(fixture.chat_a)
