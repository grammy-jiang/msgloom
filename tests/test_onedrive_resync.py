"""Pin durable OneDrive resync and content-version contracts."""

from __future__ import annotations

import pytest
from scrapy import Request
from scrapy.utils.test import get_crawler
from sqlalchemy import func, select

from message_ingest.catalog import Catalog, RawHttpEvidence
from message_ingest.catalog.models.microsoft.onedrive import (
    OneDriveContentCapture,
    OneDriveDeltaResyncAttempt,
    OneDriveDeltaResyncObservation,
    OneDriveItemRecord,
)
from message_ingest.catalog.stores.microsoft.onedrive import OneDriveStore
from message_ingest.items.microsoft.onedrive import (
    OneDriveContentItem,
    OneDriveDeltaCheckpointCandidateItem,
    OneDriveDeltaResyncAttemptItem,
    OneDriveDeltaResyncObservationItem,
    OneDriveItem,
)


def _evidence(catalog, evidence_id, run_id, observed):
    catalog.evidence.record(
        RawHttpEvidence(
            evidence_id=evidence_id,
            source_id="source",
            run_id=run_id,
            purpose="onedrive-delta-page",
            observed_at=observed,
            origin="network",
            request_fingerprint=f"fp-{evidence_id}",
            request_url="https://graph.microsoft.com/v1.0/me/drive/root/delta",
            request_method="GET",
            request_headers={},
            request_body_sha256="empty",
            request_body_path="empty.bin",
            request_body_bytes=0,
            response_url="https://graph.microsoft.com/v1.0/me/drive/root/delta",
            response_status=200,
            response_headers={},
            response_body_sha256=f"body-{evidence_id}",
            response_body_path=f"{evidence_id}.bin",
            response_body_bytes=2,
            response_flags=[],
            error_type=None,
            error_message=None,
        )
    )


def _item(raw, observed, *, run_id="old", evidence_id="old-evidence"):
    return OneDriveItem.from_graph(
        raw,
        observed_at=observed,
        evidence_id=evidence_id,
        run_id=run_id,
    )


def _candidate(run_id, base_revision, evidence_id, observed, delta_link):
    return OneDriveDeltaCheckpointCandidateItem(
        delta_link=delta_link,
        base_revision=base_revision,
        observed_at=observed,
        evidence_id=evidence_id,
        run_id=run_id,
    )


def test_resync_and_content_capture_contracts_are_additive():
    for model in (
        OneDriveContentCapture,
        OneDriveDeltaResyncAttempt,
        OneDriveDeltaResyncObservation,
    ):
        if not model.__tablename__.startswith("onedrive_"):
            pytest.fail("OneDrive additive model escaped its schema namespace")
    if OneDriveDeltaResyncAttempt is OneDriveDeltaResyncObservation:
        pytest.fail("Resync attempt and observation need distinct durable contracts")


def test_resync_request_fingerprint_separates_attempts_but_not_urls():
    from message_ingest.fingerprints.microsoft.onedrive import (
        OneDriveDeltaRequestFingerprinter,
    )

    crawler = get_crawler(
        settings_dict={
            "MSGLOOM_SOURCE_ID": "synthetic-source",
            "MSGLOOM_DATABASE_URL": "sqlite:///:memory:",
        }
    )
    fingerprinter = OneDriveDeltaRequestFingerprinter.from_crawler(crawler)
    url = "https://graph.microsoft.com/v1.0/me/drive/root/delta?token=opaque"
    old = Request(url, cb_kwargs={"reset_attempt": 0})
    reset = Request(url, cb_kwargs={"reset_attempt": 1})
    duplicate = Request(url, cb_kwargs={"reset_attempt": 1})
    if fingerprinter.fingerprint(old) == fingerprinter.fingerprint(reset):
        pytest.fail("Reset attempt must replay a URL used by the expired chain")
    if fingerprinter.fingerprint(reset) != fingerprinter.fingerprint(duplicate):
        pytest.fail("Native duplicate filtering must remain active within one reset")


def test_resync_stages_then_atomically_applies_last_server_versions_and_absence(
    tmp_path,
):
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    store = OneDriveStore(catalog, source_id="source")
    try:
        store.persist_item(
            _item(
                {"id": "seen", "name": "old", "eTag": '"old"', "file": {}},
                "2026-09-29T00:00:00+00:00",
            )
        )
        store.persist_item(
            _item(
                {"id": "absent", "name": "keep", "eTag": '"keep"', "file": {}},
                "2026-09-29T00:00:00+00:00",
            )
        )
        store.persist_item(
            _item(
                {"id": "raced", "name": "old-race", "eTag": '"r0"', "file": {}},
                "2026-09-29T00:00:00+00:00",
            )
        )
        _evidence(catalog, "base-terminal", "base-run", "2026-09-29T00:05:00+00:00")
        store.persist_candidate(
            _candidate(
                "base-run",
                None,
                "base-terminal",
                "2026-09-29T00:05:00+00:00",
                "opaque-base",
            )
        )
        if (
            store.promote_checkpoint(run_id="base-run", base_revision=None).revision
            != 1
        ):
            pytest.fail("Fixture failed to create base checkpoint")

        _evidence(catalog, "reset-trigger", "reset-run", "2026-09-29T01:00:00+00:00")
        store.persist_resync_attempt(
            OneDriveDeltaResyncAttemptItem(
                reset_attempt=1,
                base_revision=1,
                started_at="2026-09-29T01:00:00+00:00",
                trigger_evidence_id="reset-trigger",
                run_id="reset-run",
            )
        )
        _evidence(catalog, "page-1", "reset-run", "2026-09-29T01:01:00+00:00")
        for entry_index, raw in enumerate(
            (
                {"id": "seen", "name": "server", "eTag": '"server"', "file": {}},
                {"id": "new", "name": "new", "eTag": '"new"', "file": {}},
            )
        ):
            store.persist_resync_observation(
                OneDriveDeltaResyncObservationItem.from_graph(
                    raw,
                    observed_at="2026-09-29T01:01:00+00:00",
                    evidence_id="page-1",
                    run_id="reset-run",
                    reset_attempt=1,
                    base_revision=1,
                    page_number=1,
                    entry_index=entry_index,
                )
            )
        _evidence(catalog, "page-2", "reset-run", "2026-09-29T01:01:00+00:00")
        store.persist_resync_observation(
            OneDriveDeltaResyncObservationItem.from_graph(
                {"id": "seen", "deleted": {}},
                observed_at="2026-09-29T01:01:00+00:00",
                evidence_id="page-2",
                run_id="reset-run",
                reset_attempt=1,
                base_revision=1,
                page_number=2,
                entry_index=0,
            )
        )
        # A later independent metadata observation must survive reset absence.
        store.persist_item(
            _item(
                {"id": "raced", "name": "new-race", "eTag": '"r1"', "file": {}},
                "2026-09-29T01:02:00+00:00",
                run_id="discover-run",
            )
        )
        _evidence(catalog, "reset-terminal", "reset-run", "2026-09-29T01:03:00+00:00")
        store.persist_candidate(
            _candidate(
                "reset-run",
                1,
                "reset-terminal",
                "2026-09-29T01:03:00+00:00",
                "opaque-reset",
            )
        )

        with catalog.Session() as session:
            before = {
                row.item_id: row
                for row in session.scalars(select(OneDriveItemRecord)).all()
            }
            if before["seen"].name != "old" or before["absent"].is_deleted:
                pytest.fail("Staged reset observations changed current state early")
            if "new" in before:
                pytest.fail("Partial reset inserted current metadata before promotion")

        promoted = store.promote_checkpoint(
            run_id="reset-run", base_revision=1, reset_attempt=1
        )
        repeated = store.promote_checkpoint(
            run_id="reset-run", base_revision=1, reset_attempt=1
        )
        if promoted.revision != 2 or repeated.revision != 2:
            pytest.fail("Terminal reset candidate must commit exactly once")
        with catalog.Session() as session:
            rows = {
                row.item_id: row
                for row in session.scalars(select(OneDriveItemRecord)).all()
            }
            seen = rows["seen"]
            if (
                not seen.is_deleted
                or seen.name != "server"
                or seen.e_tag != '"server"'
                or seen.raw != {"id": "seen", "deleted": {}}
            ):
                pytest.fail(
                    "Last reset occurrence did not preserve prior server metadata"
                )
            absent = rows["absent"]
            if (
                not absent.is_deleted
                or absent.name != "keep"
                or absent.e_tag != '"keep"'
                or absent.deleted is not None
            ):
                pytest.fail("Authoritative absence discarded useful old metadata")
            if rows["raced"].is_deleted or rows["raced"].e_tag != '"r1"':
                pytest.fail("Reset absence superseded a newer metadata observation")
            if rows["new"].is_deleted or rows["new"].name != "new":
                pytest.fail("Clean reset failed to materialize a new server item")
            count = session.scalar(
                select(func.count()).select_from(OneDriveDeltaResyncObservation)
            )
            if count != 3:
                pytest.fail("Reset sightings must remain append-only after promotion")
    finally:
        catalog.close()


def test_stale_resync_revision_cannot_materialize_staged_state(tmp_path):
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    store = OneDriveStore(catalog, source_id="source")
    try:
        _evidence(catalog, "base", "base", "2026-09-29T00:00:00+00:00")
        store.persist_candidate(
            _candidate("base", None, "base", "2026-09-29T00:00:00+00:00", "base")
        )
        store.promote_checkpoint(run_id="base", base_revision=None)

        _evidence(catalog, "trigger", "stale", "2026-09-29T01:00:00+00:00")
        store.persist_resync_attempt(
            OneDriveDeltaResyncAttemptItem(
                reset_attempt=1,
                base_revision=1,
                started_at="2026-09-29T01:00:00+00:00",
                trigger_evidence_id="trigger",
                run_id="stale",
            )
        )
        _evidence(catalog, "staged", "stale", "2026-09-29T01:01:00+00:00")
        store.persist_resync_observation(
            OneDriveDeltaResyncObservationItem.from_graph(
                {"id": "staged-only", "name": "must-not-win"},
                observed_at="2026-09-29T01:01:00+00:00",
                evidence_id="staged",
                run_id="stale",
                reset_attempt=1,
                base_revision=1,
                page_number=1,
                entry_index=0,
            )
        )
        _evidence(catalog, "stale-terminal", "stale", "2026-09-29T01:02:00+00:00")
        store.persist_candidate(
            _candidate(
                "stale",
                1,
                "stale-terminal",
                "2026-09-29T01:02:00+00:00",
                "stale-cursor",
            )
        )

        _evidence(catalog, "winner", "winner", "2026-09-29T01:03:00+00:00")
        store.persist_candidate(
            _candidate(
                "winner",
                1,
                "winner",
                "2026-09-29T01:03:00+00:00",
                "winner-cursor",
            )
        )
        store.promote_checkpoint(run_id="winner", base_revision=1)
        with pytest.raises(ValueError, match="revision"):
            store.promote_checkpoint(run_id="stale", base_revision=1, reset_attempt=1)
        with catalog.Session() as session:
            if session.get(OneDriveItemRecord, ("source", "staged-only")) is not None:
                pytest.fail(
                    "Stale reset materialized state before losing checkpoint CAS"
                )
    finally:
        catalog.close()


def test_content_freshness_requires_exact_version_equivalence_and_keeps_history(
    tmp_path,
):
    catalog = Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")
    store = OneDriveStore(catalog, source_id="source")
    try:
        store.persist_item(
            _item(
                {"id": "file", "eTag": '"v1"', "cTag": '"c1"', "file": {}},
                "2026-09-29T00:00:00+00:00",
                evidence_id="metadata-v1",
            )
        )
        store.persist_content(
            OneDriveContentItem(
                item_id="file",
                content_sha256="digest-1",
                content_bytes=1,
                observed_at="2026-09-29T00:01:00+00:00",
                evidence_id="content-v1",
                run_id="content-run-1",
                planned_metadata_observed_at="2026-09-29T00:00:00+00:00",
                planned_metadata_evidence_id="metadata-v1",
                planned_e_tag='"v1"',
                planned_c_tag='"c1"',
                response_e_tag='"v1"',
            )
        )
        if store.content_freshness("file").status != "current":
            pytest.fail("Exact planning/response/current eTag match must prove current")

        store.persist_item(
            _item(
                {"id": "file", "eTag": '"v2"', "cTag": '"c2"', "file": {}},
                "2026-09-29T00:02:00+00:00",
                evidence_id="metadata-v2",
            )
        )
        if store.content_freshness("file").status != "stale":
            pytest.fail("Metadata version advance must make older content stale")

        store.persist_content(
            OneDriveContentItem(
                item_id="file",
                content_sha256="digest-2",
                content_bytes=2,
                observed_at="2026-09-29T00:03:00+00:00",
                evidence_id="content-unknown",
                run_id="content-run-2",
                planned_metadata_observed_at="2026-09-29T00:02:00+00:00",
                planned_metadata_evidence_id="metadata-v2",
                planned_e_tag='"v2"',
                planned_c_tag='"c2"',
                response_e_tag=None,
            )
        )
        if store.content_freshness("file").status != "unknown":
            pytest.fail("Absent response version cannot prove race-free freshness")

        store.persist_content(
            OneDriveContentItem(
                item_id="file",
                content_sha256="digest-race",
                content_bytes=2,
                observed_at="2026-09-29T00:03:30+00:00",
                evidence_id="content-race",
                run_id="content-run-race",
                planned_metadata_observed_at="2026-09-29T00:02:00+00:00",
                planned_metadata_evidence_id="metadata-v2",
                planned_e_tag='"v2"',
                planned_c_tag='"c2"',
                response_e_tag='"other"',
            )
        )
        if store.content_freshness("file").status != "stale":
            pytest.fail("Mismatched response version must expose a download race")

        store.persist_content(
            OneDriveContentItem(
                item_id="file",
                content_sha256="digest-3",
                content_bytes=3,
                observed_at="2026-09-29T00:04:00+00:00",
                evidence_id="content-v2",
                run_id="content-run-3",
                planned_metadata_observed_at="2026-09-29T00:02:00+00:00",
                planned_metadata_evidence_id="metadata-v2",
                planned_e_tag='"v2"',
                planned_c_tag='"c2"',
                response_e_tag='"v2"',
            )
        )
        state = store.content_freshness("file")
        if state.status != "current" or state.content_evidence_id != "content-v2":
            pytest.fail("Latest exact version proof was not selected")
        with catalog.Session() as session:
            captures = session.scalars(
                select(OneDriveContentCapture).order_by(
                    OneDriveContentCapture.observed_at
                )
            ).all()
            if len(captures) != 4 or captures[0].planned_c_tag != '"c1"':
                pytest.fail("Old content/version associations must remain append-only")
    finally:
        catalog.close()
