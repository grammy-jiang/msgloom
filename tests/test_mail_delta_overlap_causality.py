"""Causal authority ordering is not the terminal response's wall-clock order."""

import pytest

from message_ingest.catalog import Catalog
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)


def test_delayed_response_from_same_base_does_not_rewind_winner(tmp_path) -> None:
    """Run A starts before B yet receives its old response after B commits."""
    catalog = Catalog(f"sqlite:///{tmp_path / 'mail.db'}")
    store = OutlookDeltaCheckpointStore(catalog, "source")
    try:
        seed_url, seed_baseline = store.get_delta_start("inbox")
        if seed_url is not None:
            pytest.fail("Expected an initial absent checkpoint")
        store.write_candidate(
            baseline_identity=seed_baseline,
            run_id="seed",
            folder_id="inbox",
            delta_link="cursor-X",
            observed_at="2026-10-04T00:00:00+00:00",
        )
        store.commit("seed")
        # Both logical runs have already obtained the *same* initial cursor X.
        observed_base_a, start_identity_a = store.get_delta_start("inbox")
        observed_base_b, start_identity_b = store.get_delta_start("inbox")
        if (
            observed_base_a != observed_base_b
            or observed_base_a != "cursor-X"
            or start_identity_a != start_identity_b
        ):
            pytest.fail("Fixture did not create overlapping runs from one cursor")
        # B's provider response arrives and completes before A's delayed reply.
        store.write_candidate(
            baseline_identity=start_identity_b,
            run_id="B",
            folder_id="inbox",
            delta_link="cursor-Y",
            observed_at="2026-10-04T00:00:01+00:00",
        )
        store.commit("B")
        store.write_candidate(
            baseline_identity=start_identity_a,
            run_id="A",
            folder_id="inbox",
            delta_link="cursor-Z-from-X",
            observed_at="2026-10-04T00:00:02+00:00",
        )
        with pytest.raises(RuntimeError, match="displaced"):
            store.commit("A")
        if store.get_delta_link("inbox") != "cursor-Y":
            pytest.fail("Delayed A response superseded B's committed Graph cursor")
    finally:
        catalog.close()


def test_missing_or_legacy_candidate_proof_is_not_inferred(tmp_path) -> None:
    """Unknown start state never means explicit absent or current cursor."""
    from sqlalchemy import select

    from message_ingest.catalog.models.microsoft.outlook.email import (
        DeltaCheckpointCandidate,
        MailDeltaCandidateBase,
    )

    catalog = Catalog(f"sqlite:///{tmp_path / 'legacy.db'}")
    store = OutlookDeltaCheckpointStore(catalog, "source")
    try:
        with pytest.raises(ValueError, match="baseline"):
            store.write_candidate(
                run_id="unproved",
                folder_id="inbox",
                delta_link="X",
                observed_at="2026-10-04T00:00:00+00:00",
            )
        with catalog.writer_session() as writer:
            writer.add(
                DeltaCheckpointCandidate(
                    run_id="legacy",
                    source_id="source",
                    folder_id="inbox",
                    delta_link="legacy-token",
                    evidence_id=None,
                    observed_at="2026-10-04T00:00:00+00:00",
                )
            )
        _, identity = store.get_delta_start("inbox")
        with pytest.raises(RuntimeError, match="legacy"):
            store.write_candidate(
                baseline_identity=identity,
                run_id="legacy",
                folder_id="inbox",
                delta_link="legacy-token",
                observed_at="2026-10-04T00:00:00+00:00",
            )
        with pytest.raises(RuntimeError, match="causal baseline"):
            store.commit("legacy")
        with catalog.Session() as session:
            if (
                session.scalar(
                    select(MailDeltaCandidateBase).filter_by(
                        source_id="source",
                        run_id="legacy",
                        folder_id="inbox",
                    )
                )
                is not None
            ):
                pytest.fail("Legacy Mail candidate got retroactively trusted proof")
    finally:
        catalog.close()


def test_same_url_new_commit_generation_cannot_be_replayed_from_old_base(
    tmp_path,
) -> None:
    """A repeated opaque URL does not prove an unchanged generation."""
    catalog = Catalog(f"sqlite:///{tmp_path / 'generations.db'}")
    store = OutlookDeltaCheckpointStore(catalog, "source")
    try:
        _, first = store.get_delta_start("inbox")
        store.write_candidate(
            baseline_identity=first,
            run_id="seed",
            folder_id="inbox",
            delta_link="opaque-X",
            observed_at="2026-10-04T00:00:00+00:00",
        )
        store.commit("seed")
        _, committed = store.get_delta_start("inbox")
        store.write_candidate(
            baseline_identity=committed,
            run_id="B",
            folder_id="inbox",
            delta_link="opaque-X",
            observed_at="2026-10-04T00:00:01+00:00",
        )
        store.write_candidate(
            baseline_identity=committed,
            run_id="A",
            folder_id="inbox",
            delta_link="opaque-A",
            observed_at="2026-10-04T00:00:03+00:00",
        )
        store.commit("B")
        _, new_generation = store.get_delta_start("inbox")
        if new_generation == committed:
            pytest.fail("Reused URL lost distinct commit identity")
        store.commit("B")
        if store.get_delta_start("inbox")[1] != new_generation:
            pytest.fail("Exact winner replay changed committed generation")
        with pytest.raises(RuntimeError, match="displaced"):
            store.commit("A")
        if store.get_delta_link("inbox") != "opaque-X":
            pytest.fail("Stale replay changed the current opaque cursor")
    finally:
        catalog.close()


def test_stale_one_folder_rolls_back_whole_multifolder_promotion(tmp_path) -> None:
    """A mismatched sibling folder cannot leave half the cursors advanced."""
    from sqlalchemy import select

    from message_ingest.catalog.models.microsoft.outlook.email import (
        DeltaCheckpointCandidate,
    )

    catalog = Catalog(f"sqlite:///{tmp_path / 'multiple.db'}")
    store = OutlookDeltaCheckpointStore(catalog, "source")
    try:
        for folder in ("a", "b"):
            _, base = store.get_delta_start(folder)
            store.write_candidate(
                baseline_identity=base,
                run_id="seed",
                folder_id=folder,
                delta_link=f"{folder}-old",
                observed_at="2026-10-04T00:00:00+00:00",
            )
        store.commit("seed")
        for folder in ("b", "a"):
            _, base = store.get_delta_start(folder)
            store.write_candidate(
                baseline_identity=base,
                run_id="A",
                folder_id=folder,
                delta_link=f"{folder}-from-A",
                observed_at="2026-10-04T00:00:03+00:00",
            )
        _, base = store.get_delta_start("a")
        store.write_candidate(
            baseline_identity=base,
            run_id="B",
            folder_id="a",
            delta_link="a-new",
            observed_at="2026-10-04T00:00:02+00:00",
        )
        store.commit("B")
        with pytest.raises(RuntimeError, match="displaced"):
            store.commit("A")
        if (store.get_delta_link("a"), store.get_delta_link("b")) != ("a-new", "b-old"):
            pytest.fail("Stale A partially committed an unrelated folder")
        with catalog.Session() as session:
            rows = session.scalars(
                select(DeltaCheckpointCandidate).filter_by(
                    source_id="source",
                    run_id="A",
                )
            ).all()
            if len(rows) != 2 or any(row.committed_at is not None for row in rows):
                pytest.fail("Failed multifolder CAS escaped atomic candidate rollback")
    finally:
        catalog.close()


def test_caused_candidate_cannot_switch_initial_proof_between_pages(tmp_path) -> None:
    catalog = Catalog(f"sqlite:///{tmp_path / 'proof.db'}")
    store = OutlookDeltaCheckpointStore(catalog, "source")
    try:
        _, base = store.get_delta_start("inbox")
        store.write_candidate(
            baseline_identity=base,
            run_id="run",
            folder_id="inbox",
            delta_link="page-1",
            observed_at="2026-10-04T00:00:00+00:00",
        )
        with pytest.raises(ValueError, match="causal baseline"):
            store.write_candidate(
                baseline_identity="p:" + "a" * 64,
                run_id="run",
                folder_id="inbox",
                delta_link="page-2",
                observed_at="2026-10-04T00:00:01+00:00",
            )
        store.commit("run")
        if store.get_delta_link("inbox") != "page-1":
            pytest.fail("Rejected baseline mutation altered committed cursor")
    finally:
        catalog.close()


def test_two_independent_catalog_owners_serialize_provider_cursor_cas(tmp_path) -> None:
    """SQLite writer intent, not the per-crawler asyncio lock, owns authority."""
    url = f"sqlite:///{tmp_path / 'two-crawlers.db'}"
    owner_a = Catalog(url)
    owner_b = Catalog(url)
    try:
        a = OutlookDeltaCheckpointStore(owner_a, "same-source")
        b = OutlookDeltaCheckpointStore(owner_b, "same-source")
        _, old_a = a.get_delta_start("inbox")
        _, old_b = b.get_delta_start("inbox")
        if old_a != old_b:
            pytest.fail("Two catalog owners did not observe the same origin")
        a.write_candidate(
            baseline_identity=old_a,
            run_id="A",
            folder_id="inbox",
            delta_link="A-delta",
            observed_at="2026-10-04T00:00:02+00:00",
        )
        b.write_candidate(
            baseline_identity=old_b,
            run_id="B",
            folder_id="inbox",
            delta_link="B-delta",
            observed_at="2026-10-04T00:00:01+00:00",
        )
        b.commit("B")
        with pytest.raises(RuntimeError, match="displaced"):
            a.commit("A")
        if a.get_delta_link("inbox") != "B-delta":
            pytest.fail("Independent owner rewound an already committed cursor")
    finally:
        owner_b.close()
        owner_a.close()
