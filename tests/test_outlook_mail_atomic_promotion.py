"""Atomic lifecycle + message-delta checkpoint promotion."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from message_ingest.catalog import (
    Catalog,
    DeltaCheckpointCandidate,
    MailFolderSnapshotCandidate,
    MessagePresenceCandidate,
)
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)
from message_ingest.sync.microsoft.outlook.email.promotion import (
    ValidatedMailDeltaRun,
    promote_validated_mail_delta,
)

OLD = "2026-09-30T00:00:00+00:00"
CURRENT = "2026-10-01T00:00:00+00:00"
SOURCE = "source-1"


def _catalog(tmp_path: Path) -> Catalog:
    return Catalog(f"sqlite:///{tmp_path / 'catalog.sqlite3'}")


def _folder(store: OutlookMailStore, folder_id: str, *, run_id: str, when: str) -> None:
    store.upsert_folder(
        folder={
            "id": folder_id,
            "displayName": folder_id,
            "childFolderCount": 0,
            "totalItemCount": 0,
            "unreadItemCount": 0,
            "isHidden": False,
        },
        evidence_id=None,
        observed_at=when,
        run_id=run_id,
    )


def _message(
    store: OutlookMailStore,
    message_id: str,
    *,
    folder_id: str,
    run_id: str,
    when: str,
) -> None:
    store.record_message(
        run_id=run_id,
        message={"id": message_id, "parentFolderId": folder_id},
        kind="delta",
        evidence_id=None,
        observed_at=when,
    )


def _seed_baseline(
    catalog: Catalog,
) -> tuple[OutlookMailStore, OutlookDeltaCheckpointStore]:
    store = OutlookMailStore(catalog, source_id=SOURCE)
    checkpoints = OutlookDeltaCheckpointStore(catalog, SOURCE)
    for folder_id in ("keep", "removed"):
        _folder(store, folder_id, run_id="baseline", when=OLD)
        checkpoints.write_candidate(
            run_id="baseline",
            folder_id=folder_id,
            delta_link=f"https://graph.test/{folder_id}?$deltatoken=old",
            observed_at=OLD,
        )
    checkpoints.commit("baseline")
    _message(store, "present", folder_id="keep", run_id="baseline", when=OLD)
    _message(store, "gone", folder_id="keep", run_id="baseline", when=OLD)
    return store, checkpoints


def _stage_current(
    store: OutlookMailStore,
    checkpoints: OutlookDeltaCheckpointStore,
) -> ValidatedMailDeltaRun:
    _folder(store, "keep", run_id="current", when=CURRENT)
    store.write_folder_snapshot_candidate(
        run_id="current",
        observed_at=CURRENT,
        evidence_id=None,
    )
    store.record_message_sighting(
        run_id="current",
        message_id="present",
        observed_at=CURRENT,
        evidence_id=None,
    )
    store.write_message_presence_candidate(
        run_id="current",
        observed_at=CURRENT,
        evidence_id=None,
    )
    checkpoints.write_candidate(
        run_id="current",
        folder_id="keep",
        delta_link="https://graph.test/keep?$deltatoken=new",
        observed_at=CURRENT,
    )
    return ValidatedMailDeltaRun(
        run_id="current",
        expected_folder_ids=frozenset({"keep"}),
        reconcile_messages=True,
        candidate_folder_ids=frozenset({"keep"}),
    )


def _candidate_committed_at(catalog: Catalog) -> str | None:
    with catalog.Session() as session:
        return session.scalar(
            select(DeltaCheckpointCandidate.committed_at).filter_by(
                source_id=SOURCE,
                run_id="current",
                folder_id="keep",
            )
        )


def _snapshot_committed_at(catalog: Catalog) -> tuple[str | None, str | None]:
    with catalog.Session() as session:
        folder = session.scalar(
            select(MailFolderSnapshotCandidate.committed_at).filter_by(
                source_id=SOURCE,
                run_id="current",
            )
        )
        message = session.scalar(
            select(MessagePresenceCandidate.committed_at).filter_by(
                source_id=SOURCE,
                run_id="current",
            )
        )
        return folder, message


def test_promote_validated_mail_delta_commits_lifecycle_and_cursors_together(
    tmp_path: Path,
) -> None:
    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(store, checkpoints)

        outcome = promote_validated_mail_delta(
            catalog,
            source_id=SOURCE,
            validated=validated,
        )

        if outcome != {
            "folders_present": 1,
            "folders_absent": 1,
            "messages_present": 1,
            "messages_absent": 1,
            "committed_folders": 1,
        }:
            pytest.fail(f"Atomic promotion result changed: {outcome!r}")
        if store.folder_presence(folder_id="keep") is not True:
            pytest.fail("Current folder did not remain present")
        if store.folder_presence(folder_id="removed") is not False:
            pytest.fail("Missing folder was not atomically tombstoned")
        if store.message_presence(message_id="present") is not True:
            pytest.fail("Current message did not remain present")
        if store.message_presence(message_id="gone") is not False:
            pytest.fail("Missing message was not atomically tombstoned")
        if "$deltatoken=new" not in (checkpoints.get_delta_link("keep") or ""):
            pytest.fail("Current cursor was not promoted")
        if checkpoints.get_delta_link("removed") is not None:
            pytest.fail("Removed folder's cursor survived lifecycle promotion")
        if _candidate_committed_at(catalog) is None:
            pytest.fail("Current delta candidate was not marked committed")
        if any(value is None for value in _snapshot_committed_at(catalog)):
            pytest.fail("Lifecycle candidates were not marked committed")
    finally:
        catalog.close()


def test_promote_validated_mail_delta_rolls_back_lifecycle_when_cursor_step_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(store, checkpoints)

        def fail_checkpoint(*_args, **_kwargs):
            raise RuntimeError("private injected checkpoint failure")

        monkeypatch.setattr(
            OutlookDeltaCheckpointStore,
            "commit_in_session",
            fail_checkpoint,
        )

        with pytest.raises(RuntimeError, match="private injected checkpoint failure"):
            promote_validated_mail_delta(
                catalog,
                source_id=SOURCE,
                validated=validated,
            )

        if store.folder_presence(folder_id="removed") is not True:
            pytest.fail("Folder lifecycle mutation escaped rolled-back transaction")
        if store.message_presence(message_id="gone") is not True:
            pytest.fail("Message lifecycle mutation escaped rolled-back transaction")
        if "$deltatoken=old" not in (checkpoints.get_delta_link("keep") or ""):
            pytest.fail("Prior authoritative cursor changed after rollback")
        if "$deltatoken=old" not in (checkpoints.get_delta_link("removed") or ""):
            pytest.fail("Removed folder cursor changed after rollback")
        if _candidate_committed_at(catalog) is not None:
            pytest.fail("Delta candidate committed_at escaped rollback")
        if _snapshot_committed_at(catalog) != (None, None):
            pytest.fail("Lifecycle candidate committed_at escaped rollback")
    finally:
        catalog.close()
