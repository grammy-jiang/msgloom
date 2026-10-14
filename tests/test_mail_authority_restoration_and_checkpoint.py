"""Mailbox authority must survive restoration and out-of-order delta completion."""

import pytest

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
)
from message_ingest.sync.microsoft.outlook.email.promotion import (
    ValidatedMailDeltaRun,
    promote_validated_mail_delta,
)
from tests.test_outlook_mail_atomic_promotion import (
    SOURCE,
    _catalog,
    _folder,
    _seed_baseline,
    _stage_current,
)

LATER = "2026-10-03T00:00:00+00:00"
OLD = "2026-10-01T00:00:00+00:00"
NEW = "2026-10-02T00:00:00+00:00"


def test_mail_reconciliation_releases_restored_message_and_folder(tmp_path) -> None:
    """An absent mailbox item restored by later A1 evidence must reach A2."""
    catalog = _catalog(tmp_path)
    try:
        store, checkpoints = _seed_baseline(catalog)
        promoted = _stage_current(store, checkpoints)
        promote_validated_mail_delta(catalog, source_id=SOURCE, validated=promoted)
        if store.message_presence(message_id="gone") is not False:
            pytest.fail("Fixture did not commit message absence")
        if store.folder_presence(folder_id="removed") is not False:
            pytest.fail("Fixture did not commit folder absence")

        _folder(store, "keep", run_id="restore", when=LATER)
        _folder(store, "removed", run_id="restore", when=LATER)
        store.record_message(
            run_id="restore",
            message={"id": "gone", "parentFolderId": "keep"},
            kind="delta",
            evidence_id=None,
            observed_at=LATER,
        )
        for message in ("gone", "present"):
            store.record_message_sighting(
                run_id="restore",
                message_id=message,
                observed_at=LATER,
                evidence_id=None,
            )
        store.write_folder_snapshot_candidate(
            run_id="restore",
            observed_at=LATER,
            evidence_id=None,
        )
        store.write_message_presence_candidate(
            run_id="restore",
            observed_at=LATER,
            evidence_id=None,
        )
        for folder in ("keep", "removed"):
            checkpoints.write_candidate(
                run_id="restore",
                folder_id=folder,
                delta_link=f"https://graph.test/{folder}?$deltatoken=restored",
                observed_at=LATER,
            )
        promote_validated_mail_delta(
            catalog,
            source_id=SOURCE,
            validated=ValidatedMailDeltaRun(
                run_id="restore",
                expected_folder_ids=frozenset({"keep", "removed"}),
                reconcile_messages=True,
                candidate_folder_ids=frozenset({"keep", "removed"}),
            ),
        )
        if store.message_presence(message_id="gone") is not True:
            pytest.fail("Mutable message restoration failed")
        if store.folder_presence(folder_id="removed") is not True:
            pytest.fail("Mutable folder restoration failed")
        ledger = AcquisitionHandoffStore(catalog)
        rows = ledger.list_release_entries(
            SOURCE,
            AcquisitionStream.OUTLOOK_MAIL,
            after_seq=0,
            limit=100,
        )
        transitions = [
            fact
            for row in rows
            for fact in ledger.load_release_facts(row["release_entry_seq"])
            if fact.run_id == "restore" and fact.fact_kind == "scoped_state_transition"
        ]
        identities = {
            (fact.resource_kind, fact.resource_identity, fact.transition_reason)
            for fact in transitions
        }
        if ("message", "gone", "reconciliation_seen") not in identities:
            pytest.fail("Restored mailbox presence did not reach immutable release")
        if ("mail_folder", "removed", "inventory_present") not in identities:
            pytest.fail("Restored folder presence did not reach immutable release")
    finally:
        catalog.close()


@pytest.mark.parametrize("older_committed_first", [False, True])
def test_delayed_message_delta_candidate_cannot_rewind_cursor(
    tmp_path, older_committed_first: bool
) -> None:
    """A/B overlapping delta candidate runs must commit the newer authority."""
    catalog = _catalog(tmp_path)
    try:
        checkpoints = OutlookDeltaCheckpointStore(catalog, SOURCE)
        for run, stamp in (("older", OLD), ("newer", NEW)):
            checkpoints.write_candidate(
                run_id=run,
                folder_id="inbox",
                delta_link=f"https://graph.test/inbox?$deltatoken={run}",
                observed_at=stamp,
            )
        if older_committed_first:
            checkpoints.commit("older")
        checkpoints.commit("newer")
        with catalog.Session() as session:
            from sqlalchemy import select

            from message_ingest.catalog.models.microsoft.outlook.email import (
                DeltaCheckpoint,
            )

            before = session.scalar(
                select(DeltaCheckpoint.delta_link).filter_by(
                    source_id=SOURCE, folder_id="inbox"
                )
            )
        if before != "https://graph.test/inbox?$deltatoken=newer":
            pytest.fail("Newer cursor was not committed")
        with pytest.raises(RuntimeError, match="displaced"):
            checkpoints.commit("older")
        if checkpoints.get_delta_link("inbox") != before:
            pytest.fail("Delayed candidate rewound the last committed cursor")
        checkpoints.commit("newer")
        if checkpoints.get_delta_link("inbox") != before:
            pytest.fail("Idempotent winner replay changed the committed cursor")
    finally:
        catalog.close()
