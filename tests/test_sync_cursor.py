"""Verify provider-independent synchronization cursor contracts."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast

import pytest
from itemadapter import ItemAdapter
from scrapy.utils.test import get_crawler

from message_ingest.acquisition.contracts import EvidenceLinkedItem
from message_ingest.acquisition.evidence_link import EvidenceLinkPipeline
from message_ingest.acquisition.sync_cursor import (
    SyncCursor,
    SyncCursorCandidateItem,
    SyncScope,
    SyncStreamKey,
    canonical_scope,
)
from message_ingest.extensions.catalog import CatalogService
from message_ingest.items import RawHttpEvidenceItem
from message_ingest.pipelines.evidence import RawEvidencePipeline


def _stream(
    *,
    source_id: str = "source-1",
    provider: str = "microsoft_graph",
    resource: str = "mail.messages.delta",
    scheme: str = "microsoft_graph.mail.delta/v1",
    parameters: dict[str, str] | None = None,
) -> SyncStreamKey:
    return SyncStreamKey(
        source_id=source_id,
        provider=provider,
        resource=resource,
        scope=canonical_scope(
            scheme,
            parameters if parameters is not None else {"folder_id": "inbox"},
        ),
    )


def _candidate(
    *,
    base_revision: int | None = None,
    evidence_id: str | None = None,
    observed_at: str = "2026-09-27T00:00:00+00:00",
) -> SyncCursorCandidateItem:
    return SyncCursorCandidateItem(
        stream=_stream(),
        run_id="run-1",
        cursor=SyncCursor(
            kind="delta_link",
            value="https://graph.microsoft.com/v1.0/me/messages/delta?"
            "$deltatoken=opaque",
        ),
        base_revision=base_revision,
        observed_at=observed_at,
        evidence_id=evidence_id,
    )


def _crawler(tmp_path: Path):
    return get_crawler(
        settings_dict={
            "MSGLOOM_CATALOG_ENABLED": True,
            "MSGLOOM_RAW_EVIDENCE_ENABLED": True,
            "MSGLOOM_DATABASE_URL": f"sqlite:///{tmp_path / 'catalog.sqlite3'}",
            "MSGLOOM_RAW_EVIDENCE_DIR": str(tmp_path / "raw"),
            "MSGLOOM_SOURCE_ID": "source-1",
        }
    )


def _raw(
    evidence_id: str,
    observed_at: str,
    *,
    origin: str,
) -> RawHttpEvidenceItem:
    return RawHttpEvidenceItem(
        evidence_id=evidence_id,
        run_id="run-1",
        purpose="sync-cursor-test",
        observed_at=observed_at,
        origin=origin,
        request_fingerprint="f" * 64,
        request_url="https://graph.microsoft.com/v1.0/me/messages",
        request_method="GET",
        request_headers={"Accept": ["application/json"]},
        request_body=b"",
        response_url="https://graph.microsoft.com/v1.0/me/messages",
        response_status=200,
        response_headers={"Content-Type": ["application/json"]},
        response_body=b'{"value":[]}',
        response_flags=["cached"] if origin == "http_cache" else [],
    )


def test_scope_parameter_order_is_canonical_with_fixed_digest() -> None:
    first = canonical_scope(
        "microsoft_graph.mail.delta/v1",
        {"folder_id": "inbox", "select": "id,subject"},
    )
    second = canonical_scope(
        "microsoft_graph.mail.delta/v1",
        {"select": "id,subject", "folder_id": "inbox"},
    )

    if first != second:
        pytest.fail("Expected parameter order not to change scope equality")
    if first.canonical_json != second.canonical_json:
        pytest.fail("Expected stable canonical scope JSON")
    expected_json = (
        '{"parameters":{"folder_id":"inbox","select":"id,subject"},'
        '"scheme":"microsoft_graph.mail.delta/v1"}'
    )
    if first.canonical_json != expected_json:
        pytest.fail(f"Unexpected canonical JSON: {first.canonical_json}")
    if (
        first.scope_id
        != "68850cd57d5a2efe3bc4200e0c965f142ab0d6fbddc2f5550f4ee72275518f5a"
    ):
        pytest.fail(f"Unexpected fixed scope digest: {first.scope_id}")


@pytest.mark.parametrize(
    "other",
    [
        _stream(source_id="source-2"),
        _stream(provider="google"),
        _stream(resource="calendar.events.delta"),
        _stream(scheme="microsoft_graph.mail.delta/v2"),
        _stream(parameters={"folder_id": "archive"}),
        _stream(
            resource="calendar.events.delta",
            scheme="microsoft_graph.calendar_view.delta/v1",
            parameters={
                "calendar_id": "primary",
                "start_datetime": "2026-09-01T00:00:00Z",
                "end_datetime": "2026-10-01T00:00:00Z",
            },
        ),
        _stream(
            resource="calendar.events.delta",
            scheme="microsoft_graph.calendar_view.delta/v1",
            parameters={
                "calendar_id": "primary",
                "start_datetime": "2026-09-02T00:00:00Z",
                "end_datetime": "2026-10-01T00:00:00Z",
            },
        ),
    ],
)
def test_stream_identity_changes_when_any_scope_dimension_changes(
    other: SyncStreamKey,
) -> None:
    if other == _stream():
        pytest.fail("Expected changed stream dimension to produce a new stream")


def test_calendar_window_end_changes_scope_identity() -> None:
    one = canonical_scope(
        "microsoft_graph.calendar_view.delta/v1",
        {
            "calendar_id": "primary",
            "start_datetime": "2026-09-01T00:00:00Z",
            "end_datetime": "2026-10-01T00:00:00Z",
        },
    )
    two = canonical_scope(
        "microsoft_graph.calendar_view.delta/v1",
        {
            "calendar_id": "primary",
            "start_datetime": "2026-09-01T00:00:00Z",
            "end_datetime": "2026-11-01T00:00:00Z",
        },
    )
    if one.scope_id == two.scope_id:
        pytest.fail("Expected Calendar window end to participate in scope identity")


def test_scope_copies_mapping_and_preserves_parameter_values_exactly() -> None:
    parameters = {"folder_id": " opaque folder id "}
    scope = canonical_scope("mail/v1", parameters)
    parameters["folder_id"] = "changed"

    if dict(scope.parameters) != {"folder_id": " opaque folder id "}:
        pytest.fail("Expected scope to copy input and preserve opaque values")


def test_direct_scope_construction_rejects_duplicate_parameter_names() -> None:
    with pytest.raises(ValueError, match="duplicate scope parameter"):
        SyncScope(
            scheme="mail/v1",
            parameters=(("folder_id", "one"), ("folder_id", "two")),
        )


@pytest.mark.parametrize(
    ("factory", "error_type"),
    [
        (lambda: canonical_scope("", {}), ValueError),
        (lambda: canonical_scope(" mail/v1", {}), ValueError),
        (lambda: canonical_scope("mail/v1", {" bad": "x"}), ValueError),
        (lambda: SyncScope("mail/v1", cast(Any, (("key", 1),))), TypeError),
        (
            lambda: SyncStreamKey("", "microsoft_graph", "mail", canonical_scope("x", {})),
            ValueError,
        ),
        (
            lambda: SyncStreamKey(
                "source",
                " microsoft_graph",
                "mail",
                canonical_scope("x", {}),
            ),
            ValueError,
        ),
        (
            lambda: SyncStreamKey(
                "source",
                "microsoft_graph",
                "",
                canonical_scope("x", {}),
            ),
            ValueError,
        ),
    ],
)
def test_invalid_scope_and_stream_fields_are_rejected(factory, error_type) -> None:
    with pytest.raises(error_type):
        factory()


def test_cursor_values_are_opaque_and_hidden_from_repr() -> None:
    graph_value = (
        "https://graph.microsoft.com/v1.0/me/messages/delta?"
        "$deltatoken=A%2FB%3D%3D"
    )
    history_value = "999999999999999999999999999999999999"
    graph = SyncCursor(kind="delta_link", value=graph_value)
    gmail = SyncCursor(kind="history_id", value=history_value)

    if graph.value != graph_value or gmail.value != history_value:
        pytest.fail("Expected cursor values to be preserved exactly")
    if graph_value in repr(graph) or history_value in repr(gmail):
        pytest.fail("Expected opaque cursor values to stay out of repr")


@pytest.mark.parametrize(
    ("kind", "value", "error_type"),
    [
        ("page_token", "opaque", ValueError),
        (1, "opaque", TypeError),
        ("delta_link", "", ValueError),
        ("delta_link", 1, TypeError),
    ],
)
def test_invalid_cursor_fields_are_rejected(kind, value, error_type) -> None:
    with pytest.raises(error_type):
        SyncCursor(kind=kind, value=value)


@pytest.mark.parametrize("base_revision", [None, 1, 42])
def test_candidate_accepts_uncommitted_or_positive_base_revision(
    base_revision: int | None,
) -> None:
    candidate = _candidate(base_revision=base_revision)
    if candidate.base_revision != base_revision:
        pytest.fail("Expected candidate base revision to be preserved")


@pytest.mark.parametrize(
    ("base_revision", "error_type"),
    [
        (0, ValueError),
        (-1, ValueError),
        (True, TypeError),
        (1.5, TypeError),
        ("1", TypeError),
    ],
)
def test_candidate_rejects_invalid_base_revision(
    base_revision,
    error_type,
) -> None:
    with pytest.raises(error_type):
        _candidate(base_revision=base_revision)


def test_candidate_is_evidence_linked_and_itemadapter_compatible() -> None:
    candidate = _candidate(evidence_id=None)
    if not isinstance(candidate, EvidenceLinkedItem):
        pytest.fail("Expected sync cursor candidate to satisfy EvidenceLinkedItem")

    adapter = ItemAdapter(candidate)
    if set(adapter.field_names()) != {
        "stream",
        "run_id",
        "cursor",
        "base_revision",
        "observed_at",
        "evidence_id",
    }:
        pytest.fail(f"Unexpected candidate adapter fields: {adapter.field_names()}")


def test_evidence_link_pipeline_canonicalizes_candidate_without_other_mutation(
    tmp_path: Path,
) -> None:
    crawler = _crawler(tmp_path)
    raw_pipeline = RawEvidencePipeline.from_crawler(crawler)
    link_pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    original = _raw(
        "evidence-original",
        "2026-09-27T00:00:00+00:00",
        origin="network",
    )
    replay = _raw(
        "evidence-replay",
        "2026-09-27T01:00:00+00:00",
        origin="http_cache",
    )
    asyncio.run(raw_pipeline.process_item(original))
    asyncio.run(raw_pipeline.process_item(replay))

    candidate = _candidate(
        base_revision=7,
        evidence_id="evidence-replay",
        observed_at="2026-09-27T01:00:00+00:00",
    )
    stream = candidate.stream
    cursor = candidate.cursor
    run_id = candidate.run_id
    base_revision = candidate.base_revision

    asyncio.run(link_pipeline.process_item(candidate))

    if candidate.evidence_id != "evidence-original":
        pytest.fail("Expected candidate evidence alias to become canonical")
    if candidate.observed_at != "2026-09-27T00:00:00+00:00":
        pytest.fail("Expected candidate capture timestamp to become canonical")
    if (
        candidate.stream is not stream
        or candidate.cursor is not cursor
        or candidate.run_id != run_id
        or candidate.base_revision != base_revision
    ):
        pytest.fail("Expected evidence linking not to mutate sync cursor semantics")
    raw_pipeline.close_spider()


def test_missing_evidence_still_blocks_cursor_candidate(tmp_path: Path) -> None:
    crawler = _crawler(tmp_path)
    pipeline = EvidenceLinkPipeline.from_crawler(crawler)
    candidate = _candidate(
        evidence_id="missing-evidence",
        observed_at="2026-09-27T01:00:00+00:00",
    )

    with pytest.raises(RuntimeError, match="raw HTTP evidence"):
        asyncio.run(pipeline.process_item(candidate))

    if candidate.evidence_id != "missing-evidence":
        pytest.fail("Expected failed evidence validation not to mutate candidate")
    CatalogService.from_crawler(crawler).spider_closed(None, "test-finished")
