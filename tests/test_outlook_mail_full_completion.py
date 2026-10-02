"""Current-attempt Full-v1 completion proof for rule-planned refresh."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import event

from message_ingest.acquisition.microsoft.outlook.email.full_completion import (
    verify_current_full_v1,
)
from message_ingest.acquisition.microsoft.outlook.email.profile import FULL_V1
from message_ingest.catalog import Catalog
from message_ingest.catalog.models.acquisition import RawHttpEvidence
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore

SOURCE = "source-1"
MESSAGE = "message-1"
CURRENT_RUN = "run-current"
OLD_RUN = "run-old"
NOW = "2026-10-02T00:00:00+00:00"


def _catalog(tmp_path: Path) -> Catalog:
    return Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")


def _evidence(
    catalog: Catalog,
    evidence_id: str,
    *,
    run_id: str,
    purpose: str,
    origin: str = "network",
) -> None:
    row = RawHttpEvidence(
        evidence_id=evidence_id,
        source_id=SOURCE,
        run_id=run_id,
        purpose=purpose,
        observed_at=NOW,
        origin=origin,
        request_fingerprint=(evidence_id[0] if evidence_id else "0") * 64,
        request_url="https://example.test/synthetic",
        request_method="GET",
        request_headers={},
        request_body_sha256="0" * 64,
        request_body_path="",
        request_body_bytes=0,
        response_url="https://example.test/synthetic",
        response_status=200,
        response_headers={},
        response_body_sha256="1" * 64,
        response_body_path="synthetic",
        response_body_bytes=2,
        response_flags=[],
        error_type=None,
        error_message=None,
    )
    with catalog.Session() as session, session.begin():
        session.add(row)


def _surface(
    store: OutlookMailStore,
    surface: str,
    status: str,
    evidence_id: str,
) -> None:
    store.set_surface(
        message_id=MESSAGE,
        surface=surface,
        status=status,
        evidence_id=evidence_id,
        observed_at=NOW,
        profile_version=FULL_V1,
    )


def _base_current(catalog: Catalog, store: OutlookMailStore) -> None:
    for surface, purpose in (
        ("detail", "message-detail"),
        ("mime", "message-mime"),
        ("attachments", "attachments-list"),
    ):
        evidence_id = f"e-{surface}"
        _evidence(catalog, evidence_id, run_id=CURRENT_RUN, purpose=purpose)
        _surface(store, surface, "acquired", evidence_id)


def test_current_run_acquired_surfaces_and_child_are_complete(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        _base_current(catalog, store)
        _evidence(
            catalog,
            "e-child",
            run_id=CURRENT_RUN,
            purpose="attachment-raw",
        )
        store.upsert_attachment(
            message_id=MESSAGE,
            attachment={
                "id": "a1",
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": "a1.bin",
                "size": 2,
                "isInline": False,
            },
            evidence_id="e-attachments",
            observed_at=NOW,
        )
        _surface(store, "attachment_raw:a1", "acquired", "e-child")

        result = verify_current_full_v1(
            catalog,
            source_id=SOURCE,
            run_id=CURRENT_RUN,
            message_ids=(MESSAGE,),
        )

        if not result.complete or result.with_limitations:
            pytest.fail(f"Current acquired Full-v1 should be complete: {result!r}")
        if result.reason_code != "terminal_complete":
            pytest.fail("Complete result used the wrong bounded reason")
        if result.waivable_failure_reasons:
            pytest.fail("Acquired Full-v1 unexpectedly produced waivable failures")
    finally:
        catalog.close()


def test_profile_terminal_provider_limitations_are_complete_and_waivable(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        cases = (
            ("detail", "unauthorized", "message-detail"),
            ("mime", "unavailable", "message-mime"),
            ("attachments", "unsupported", "attachments-list"),
        )
        for surface, status, purpose in cases:
            evidence_id = f"e-{surface}"
            _evidence(catalog, evidence_id, run_id=CURRENT_RUN, purpose=purpose)
            _surface(store, surface, status, evidence_id)

        result = verify_current_full_v1(
            catalog,
            source_id=SOURCE,
            run_id=CURRENT_RUN,
            message_ids=(MESSAGE,),
        )

        if not result.complete or not result.with_limitations:
            pytest.fail(f"Terminal limitations should satisfy Full-v1: {result!r}")
        if result.reason_code != "terminal_complete_with_limitations":
            pytest.fail("Terminal-limitation result used the wrong reason")
        if result.waivable_failure_reasons != frozenset(
            {
                "request_failure:message-detail",
                "request_failure:message-mime",
                "request_failure:attachments-list",
            }
        ):
            pytest.fail(f"Unexpected waivable failure set: {result!r}")
    finally:
        catalog.close()


def test_old_base_surface_cannot_satisfy_current_refresh(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        _base_current(catalog, store)
        _evidence(catalog, "e-detail-old", run_id=OLD_RUN, purpose="message-detail")
        _surface(store, "detail", "acquired", "e-detail-old")

        result = verify_current_full_v1(
            catalog,
            source_id=SOURCE,
            run_id=CURRENT_RUN,
            message_ids=(MESSAGE,),
        )

        if result.complete or result.reason_code != "incomplete":
            pytest.fail("Old detail evidence incorrectly satisfied current refresh")
    finally:
        catalog.close()


def test_current_attachment_inventory_requires_current_child_surface(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        _base_current(catalog, store)
        store.upsert_attachment(
            message_id=MESSAGE,
            attachment={
                "id": "a1",
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": "a1.bin",
            },
            evidence_id="e-attachments",
            observed_at=NOW,
        )
        _evidence(catalog, "e-child-old", run_id=OLD_RUN, purpose="attachment-raw")
        _surface(store, "attachment_raw:a1", "acquired", "e-child-old")

        result = verify_current_full_v1(
            catalog,
            source_id=SOURCE,
            run_id=CURRENT_RUN,
            message_ids=(MESSAGE,),
        )

        if result.complete:
            pytest.fail("Old attachment child surface satisfied current inventory")
    finally:
        catalog.close()


def test_old_attachment_row_not_seen_in_current_inventory_is_ignored(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        _evidence(catalog, "e-old-meta", run_id=OLD_RUN, purpose="attachments-list")
        store.upsert_attachment(
            message_id=MESSAGE,
            attachment={
                "id": "deleted-old",
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": "old.bin",
            },
            evidence_id="e-old-meta",
            observed_at="2026-10-01T00:00:00+00:00",
        )
        _base_current(catalog, store)

        result = verify_current_full_v1(
            catalog,
            source_id=SOURCE,
            run_id=CURRENT_RUN,
            message_ids=(MESSAGE,),
        )

        if not result.complete:
            pytest.fail("Historical attachment row blocked empty current inventory")
    finally:
        catalog.close()


def test_missing_required_surface_is_incomplete(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    try:
        store = OutlookMailStore(catalog, source_id=SOURCE)
        for surface, purpose in (
            ("detail", "message-detail"),
            ("attachments", "attachments-list"),
        ):
            evidence_id = f"e-{surface}"
            _evidence(catalog, evidence_id, run_id=CURRENT_RUN, purpose=purpose)
            _surface(store, surface, "acquired", evidence_id)

        result = verify_current_full_v1(
            catalog,
            source_id=SOURCE,
            run_id=CURRENT_RUN,
            message_ids=(MESSAGE,),
        )

        if result.complete or result.reason_code != "incomplete":
            pytest.fail("Missing MIME surface did not fail completion proof")
    finally:
        catalog.close()


def test_empty_target_set_is_terminal_complete() -> None:
    catalog = Catalog("sqlite:///:memory:")
    try:
        result = verify_current_full_v1(
            catalog,
            source_id=SOURCE,
            run_id=CURRENT_RUN,
            message_ids=(),
        )
        if not result.complete or result.reason_code != "terminal_complete":
            pytest.fail("Empty Full target set must be vacuously complete")
    finally:
        catalog.close()


def test_bulk_evidence_provenance_queries_are_chunked(tmp_path: Path) -> None:
    catalog = _catalog(tmp_path)
    try:
        rows = [
            RawHttpEvidence(
                evidence_id=f"bulk-{index}",
                source_id=SOURCE,
                run_id=CURRENT_RUN,
                purpose="bulk-provenance",
                observed_at=NOW,
                origin="network",
                request_fingerprint=f"{index:064x}",
                request_url="https://example.test/bulk",
                request_method="GET",
                request_headers={},
                request_body_sha256="0" * 64,
                request_body_path="",
                request_body_bytes=0,
                response_url="https://example.test/bulk",
                response_status=200,
                response_headers={},
                response_body_sha256="1" * 64,
                response_body_path="synthetic",
                response_body_bytes=2,
                response_flags=[],
                error_type=None,
                error_message=None,
            )
            for index in range(1001)
        ]
        with catalog.Session() as session, session.begin():
            session.add_all(rows)

        parameter_counts: list[int] = []

        def before_cursor_execute(
            _conn,
            _cursor,
            statement: str,
            parameters,
            _context,
            _executemany: bool,
        ) -> None:
            if "SELECT" not in statement or "raw_http_evidence" not in statement:
                return
            if isinstance(parameters, tuple):
                parameter_counts.append(len(parameters))

        event.listen(catalog.engine, "before_cursor_execute", before_cursor_execute)
        try:
            result = catalog.evidence.run_ids_for(
                tuple(f"bulk-{index}" for index in range(1001))
            )
        finally:
            event.remove(catalog.engine, "before_cursor_execute", before_cursor_execute)

        if len(result) != 1001 or set(result.values()) != {CURRENT_RUN}:
            pytest.fail("Chunked provenance query lost evidence/run mappings")
        if len(parameter_counts) < 3:
            pytest.fail(
                f"Bulk provenance was not split into bounded chunks: {parameter_counts!r}"
            )
        if max(parameter_counts, default=0) > 500:
            pytest.fail(
                f"Bulk provenance exceeded the 500-ID query bound: {parameter_counts!r}"
            )
    finally:
        catalog.close()
