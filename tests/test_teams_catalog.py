"""Core Teams schema, scoped identity, history, and projection tests."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import inspect, select

from message_ingest.catalog.models.acquisition import SourceBinding
from message_ingest.catalog.models.microsoft.teams import (
    TeamsMessageCurrent,
    TeamsMessageObservation,
)
from message_ingest.catalog.stores.microsoft.teams.message import TeamsMessageStore
from tests.teams_persistence_support import (
    OBSERVED,
    SOURCE,
    chat_message,
    open_catalog,
    record_evidence,
)


def _later(seconds: int) -> str:
    """Return an offset-aware instant relative to the shared fixture time."""
    from datetime import datetime

    return (datetime.fromisoformat(OBSERVED) + timedelta(seconds=seconds)).isoformat()


def test_dedicated_model_import_adds_schema_without_losing_existing_rows(
    tmp_path: Path,
) -> None:
    catalog = open_catalog(tmp_path)
    with catalog.writer_session() as session:
        session.add(
            SourceBinding(
                source_id="existing-source",
                provider="microsoft",
                key_scheme="test",
                account_key_sha256="0" * 64,
                binding_method="test",
                bound_at=OBSERVED,
            )
        )
    catalog.close()

    reopened = open_catalog(tmp_path)
    try:
        table_names = set(inspect(reopened.engine).get_table_names())
        required = {
            "teams_message_observations",
            "teams_message_current",
            "teams_message_deletions",
            "teams_message_attachments",
            "teams_topology_observations",
            "teams_topology_current",
            "teams_reference_resolution_observations",
            "teams_reference_resolution_current",
            "teams_hosted_content_observations",
            "teams_coverage_observations",
            "teams_coverage_current",
        }
        missing = required - table_names
        if missing:
            pytest.fail(
                f"Dedicated Teams model registration missed tables: {missing!r}"
            )
        with reopened.Session() as session:
            binding = session.get(SourceBinding, "existing-source")
            if binding is None:
                pytest.fail("Additive Teams schema initialization lost an existing row")
    finally:
        reopened.close()


def test_scoped_message_ids_and_sources_never_collide(tmp_path: Path) -> None:
    catalog = open_catalog(tmp_path)
    try:
        cases = [
            ("source-a", "chat-a", "ev-a"),
            ("source-a", "chat-b", "ev-b"),
            ("source-b", "chat-a", "ev-c"),
        ]
        for source_id, chat_id, evidence_id in cases:
            record_evidence(catalog, evidence_id, source_id=source_id)
            item = chat_message(
                source_id=source_id,
                chat_id=chat_id,
                evidence_id=evidence_id,
            )
            TeamsMessageStore(catalog, source_id=source_id).persist_message(item)

        with catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageObservation)).all()
            if len(rows) != 3:
                pytest.fail(f"Expected three scoped observations, got {len(rows)}")
            digests = {row.scope_key_sha256 for row in rows}
            if len(digests) != 2:
                pytest.fail("Chat scope must distinguish duplicate message IDs")
            source_scopes = {(row.source_id, row.scope_key_sha256) for row in rows}
            if len(source_scopes) != 3:
                pytest.fail("Source identity must participate in durable message keys")
    finally:
        catalog.close()


def test_message_history_keeps_versions_same_etag_and_exact_replay(
    tmp_path: Path,
) -> None:
    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(catalog, source_id=SOURCE)
    try:
        first = chat_message(evidence_id="ev-1", etag="opaque", body="one")
        second = chat_message(
            evidence_id="ev-2",
            observed_at=_later(10),
            etag="opaque",
            body="two",
        )
        record_evidence(catalog, "ev-1")
        record_evidence(catalog, "ev-2", observed_at=_later(10))

        if store.persist_message(first) != "created":
            pytest.fail("First message observation should create current state")
        if store.persist_message(second) != "advanced":
            pytest.fail("Later capture with unchanged etag must still be retained")
        if store.persist_message(second) != "replay":
            pytest.fail("Exact scoped evidence replay must be idempotent")

        with catalog.Session() as session:
            observations = session.scalars(
                select(TeamsMessageObservation).order_by(
                    TeamsMessageObservation.observation_id
                )
            ).all()
            if len(observations) != 2:
                pytest.fail(
                    "Distinct responses with one etag must retain two observations"
                )
            current = session.scalar(select(TeamsMessageCurrent))
            if current is None:
                pytest.fail("Expected current message projection")
            if current.raw is None or current.raw["body"]["content"] != "two":
                pytest.fail(
                    "Latest strictly newer capture should own current projection"
                )
            if current.latest_observed_at != _later(10):
                pytest.fail("Exact replay must not advance current capture time")
    finally:
        catalog.close()


def test_stale_and_equal_time_message_observations_do_not_regress_current(
    tmp_path: Path,
) -> None:
    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(catalog, source_id=SOURCE)
    try:
        newer_at = _later(20)
        equal_at = newer_at
        stale_at = _later(10)
        for evidence_id, observed_at in (
            ("ev-new", newer_at),
            ("ev-equal", equal_at),
            ("ev-stale", stale_at),
        ):
            record_evidence(catalog, evidence_id, observed_at=observed_at)

        newer = chat_message(
            evidence_id="ev-new",
            observed_at=newer_at,
            etag="etag-new",
            body="new",
        )
        equal = chat_message(
            evidence_id="ev-equal",
            observed_at=equal_at,
            etag="etag-equal",
            body="equal-competitor",
        )
        stale = chat_message(
            evidence_id="ev-stale",
            observed_at=stale_at,
            etag="etag-stale",
            body="stale",
        )
        store.persist_message(newer)
        if store.persist_message(equal) != "tie":
            pytest.fail("Equal-time competing observation must be retained as a tie")
        if store.persist_message(stale) != "stale":
            pytest.fail("Older observation must be retained without current regression")

        with catalog.Session() as session:
            observations = session.scalars(select(TeamsMessageObservation)).all()
            if len(observations) != 3:
                pytest.fail(
                    "Stale and equal-time observations must remain immutable history"
                )
            current = session.scalar(select(TeamsMessageCurrent))
            if current is None:
                pytest.fail("Expected current message projection")
            if current.raw is None or current.raw["body"]["content"] != "new":
                pytest.fail(
                    "Opaque etags must never order stale/equal current projection"
                )
    finally:
        catalog.close()


def test_channel_root_and_reply_scopes_keep_duplicate_ids_distinct(
    tmp_path: Path,
) -> None:
    from message_ingest.items.microsoft.teams.message import TeamsMessageItem

    catalog = open_catalog(tmp_path)
    store = TeamsMessageStore(catalog, source_id=SOURCE)
    try:
        cases = (
            ("root-a", None, "channel-root-evidence"),
            ("root-b", None, "channel-root-evidence-2"),
            ("root-a", "same-message", "channel-reply-evidence"),
        )
        for index, (root_id, reply_id, evidence_id) in enumerate(cases):
            observed_at = f"2026-10-04T00:10:0{index}+00:00"
            record_evidence(catalog, evidence_id, observed_at=observed_at)
            raw = {
                "id": reply_id or "same-message",
                "etag": f"etag-{index}",
                "body": {"contentType": "html", "content": root_id},
            }
            if reply_id is None:
                item = TeamsMessageItem.from_channel_root_graph(
                    raw,
                    team_id="team-a",
                    channel_id=f"channel-{index}",
                    source_id=SOURCE,
                    observed_at=observed_at,
                    evidence_id=evidence_id,
                    run_id="run-current",
                )
            else:
                item = TeamsMessageItem.from_channel_reply_graph(
                    raw,
                    team_id="team-a",
                    channel_id="channel-a",
                    root_message_id=root_id,
                    source_id=SOURCE,
                    observed_at=observed_at,
                    evidence_id=evidence_id,
                    run_id="run-current",
                )
            store.persist_message(item)

        with catalog.Session() as session:
            rows = session.scalars(select(TeamsMessageObservation)).all()
            if len(rows) != 3:
                pytest.fail("Expected three channel root/reply observations")
            if len({row.scope_key_sha256 for row in rows}) != 3:
                pytest.fail("Channel root/reply context must scope duplicate IDs")
    finally:
        catalog.close()
