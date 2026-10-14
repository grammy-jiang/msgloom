"""Mailbox folder-delta authority must follow cursor ancestry, not arrival time."""

from pathlib import Path

import pytest

from message_ingest.catalog import Catalog
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookFolderDeltaCheckpointStore,
)


def test_delayed_folder_delta_response_from_stale_start_is_rejected(tmp_path: Path):
    """Runs A and B use X; B commits Y; late A must never replace Y with Z."""
    catalog = Catalog(f"sqlite:///{tmp_path / 'mail.db'}")
    try:
        store = OutlookFolderDeltaCheckpointStore(catalog, "source")
        _, seed_base = store.get_delta_start()
        store.write_candidate(
            baseline_identity=seed_base,
            run_id="seed",
            delta_link="cursor-X",
            observed_at="2026-10-14T00:00:00+00:00",
        )
        store.commit("seed")
        start_a, base_a = store.get_delta_start()
        start_b, base_b = store.get_delta_start()
        if (start_a, start_b) != ("cursor-X", "cursor-X") or base_a != base_b:
            pytest.fail("Racing Graph crawls did not start from the same X")
        store.write_candidate(
            baseline_identity=base_b,
            run_id="B",
            delta_link="cursor-Y",
            observed_at="2026-10-14T00:00:01+00:00",
        )
        store.commit("B")
        store.write_candidate(
            baseline_identity=base_a,
            run_id="A",
            delta_link="cursor-Z-from-X",
            observed_at="2026-10-14T00:00:02+00:00",
        )
        with pytest.raises(RuntimeError, match="displaced"):
            store.commit("A")
        if store.get_delta_link() != "cursor-Y":
            pytest.fail("Delayed old Graph response rewound mailbox authority")
    finally:
        catalog.close()


def test_same_opaque_url_new_folder_commit_generation_invalidates_old_run(
    tmp_path: Path,
):
    """A repeated delta URL does not erase owner/commit generation ancestry."""
    catalog = Catalog(f"sqlite:///{tmp_path / 'same-url.db'}")
    try:
        store = OutlookFolderDeltaCheckpointStore(catalog, "source")
        _, absent = store.get_delta_start()
        store.write_candidate(
            baseline_identity=absent,
            run_id="seed",
            delta_link="cursor-X",
            observed_at="2026-10-14T00:00:00+00:00",
        )
        store.commit("seed")
        _, generation = store.get_delta_start()
        store.write_candidate(
            baseline_identity=generation,
            run_id="B",
            delta_link="cursor-X",
            observed_at="2026-10-14T00:00:01+00:00",
        )
        store.write_candidate(
            baseline_identity=generation,
            run_id="A",
            delta_link="stale-Z",
            observed_at="2026-10-14T00:00:02+00:00",
        )
        store.commit("B")
        _, new_generation = store.get_delta_start()
        if new_generation == generation:
            pytest.fail("The same Graph cursor URL erased a committed generation")
        store.commit("B")
        if store.get_delta_start()[1] != new_generation:
            pytest.fail("Idempotent committed replay churned cursor generation")
        with pytest.raises(RuntimeError, match="displaced"):
            store.commit("A")
        if store.get_delta_link() != "cursor-X":
            pytest.fail("Stale same-URL competing folder delta rewound authority")
    finally:
        catalog.close()


def test_missing_or_legacy_folder_candidate_proof_cannot_be_inferred(tmp_path: Path):
    """A pre-migration pending cursor is not an authorized baseline."""
    from sqlalchemy import select

    from message_ingest.catalog.models.microsoft.outlook.email import (
        FolderDeltaCheckpointCandidate,
        MailFolderDeltaCandidateBase,
    )

    catalog = Catalog(f"sqlite:///{tmp_path / 'legacy.db'}")
    try:
        store = OutlookFolderDeltaCheckpointStore(catalog, "source")
        with pytest.raises(ValueError, match="baseline"):
            store.write_candidate(
                run_id="unproved",
                delta_link="X",
                observed_at="2026-10-14T00:00:00+00:00",
            )
        with catalog.writer_session() as writer:
            writer.add(
                FolderDeltaCheckpointCandidate(
                    source_id="source",
                    run_id="legacy",
                    delta_link="legacy-X",
                    observed_at="2026-10-14T00:00:01+00:00",
                    evidence_id=None,
                )
            )
        _, current = store.get_delta_start()
        with pytest.raises(RuntimeError, match="legacy"):
            store.write_candidate(
                baseline_identity=current,
                run_id="legacy",
                delta_link="legacy-X",
                observed_at="2026-10-14T00:00:01+00:00",
            )
        with pytest.raises(RuntimeError, match="causal baseline"):
            store.commit("legacy")
        with catalog.Session() as session:
            if (
                session.scalar(
                    select(MailFolderDeltaCandidateBase).filter_by(
                        source_id="source",
                        run_id="legacy",
                    )
                )
                is not None
            ):
                pytest.fail("Legacy pending cursor gained fabricated proof")
    finally:
        catalog.close()


def test_two_catalog_owners_share_atomic_folder_delta_cas(tmp_path: Path):
    """A shared SQLite writer, not a per-Spider lock, orders mailbox commits."""
    url = f"sqlite:///{tmp_path / 'owners.db'}"
    cat_a = Catalog(url)
    cat_b = Catalog(url)
    try:
        a = OutlookFolderDeltaCheckpointStore(cat_a, "source")
        b = OutlookFolderDeltaCheckpointStore(cat_b, "source")
        _, base_a = a.get_delta_start()
        _, base_b = b.get_delta_start()
        if base_a != base_b:
            pytest.fail("Two independent Catalog owners disagreed on baseline")
        a.write_candidate(
            baseline_identity=base_a,
            run_id="A",
            delta_link="A",
            observed_at="2026-10-14T00:00:02+00:00",
        )
        b.write_candidate(
            baseline_identity=base_b,
            run_id="B",
            delta_link="B",
            observed_at="2026-10-14T00:00:01+00:00",
        )
        b.commit("B")
        with pytest.raises(RuntimeError, match="displaced"):
            a.commit("A")
        if a.get_delta_link() != "B":
            pytest.fail("Independent Catalog owner bypassed folder delta CAS")
    finally:
        cat_b.close()
        cat_a.close()


def test_folder_delta_causal_baseline_is_immutable(tmp_path: Path):
    """A staged run cannot adopt another cursor generation mid-pagination."""
    catalog = Catalog(f"sqlite:///{tmp_path / 'immutable.db'}")
    try:
        store = OutlookFolderDeltaCheckpointStore(catalog, "source")
        _, baseline = store.get_delta_start()
        store.write_candidate(
            baseline_identity=baseline,
            run_id="run",
            delta_link="next-link",
            observed_at="2026-10-14T00:00:00+00:00",
        )
        with pytest.raises(ValueError, match="causal baseline"):
            store.write_candidate(
                baseline_identity="p:" + "a" * 64,
                run_id="run",
                delta_link="changed",
                observed_at="2026-10-14T00:00:01+00:00",
            )
        store.commit("run")
        if store.get_delta_link() != "next-link":
            pytest.fail("Rejected proof mutation changed the committed cursor")
    finally:
        catalog.close()
