"""Winning Mail cursor authority must not lose work to later failed crawls."""

import pytest
from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionStream
from message_ingest.catalog.models.microsoft.outlook.email import (
    MessageRecord,
)
from message_ingest.catalog.stores.handoff import AcquisitionHandoffStore
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
    OutlookFolderDeltaCheckpointStore,
)
from message_ingest.sync.microsoft.outlook.email.promotion import (
    promote_validated_mail_delta,
)
from tests.test_outlook_mail_atomic_promotion import (
    CURRENT,
    SOURCE,
    _catalog,
    _folder,
    _seed_baseline,
    _stage_current,
)

LATER = "2026-10-02T00:00:00+00:00"


@pytest.mark.parametrize("loser_when", ["2026-09-30T12:00:00+00:00", CURRENT, LATER])
def test_losing_message_delta_cannot_suppress_winning_message_release(
    tmp_path, loser_when
):
    """B(v2) stages; A(v1) writes later; only B commits provider cursor."""
    catalog = _catalog(tmp_path)
    try:
        winner, checkpoints = _seed_baseline(catalog)
        validated = _stage_current(winner, checkpoints)
        accepted = winner.record_message(
            run_id="current",
            kind="delta",
            observed_at=CURRENT,
            evidence_id=None,
            message={
                "id": "present",
                "parentFolderId": "keep",
                "changeKey": "v2",
                "subject": "winning-subject",
            },
        )
        baseline_a = checkpoints.get_delta_start("keep")[1]
        loser = OutlookMailStore(catalog, source_id=SOURCE)
        ignored = loser.record_message(
            run_id="losing",
            kind="delta",
            observed_at=loser_when,
            evidence_id=None,
            message={
                "id": "present",
                "parentFolderId": "keep",
                "changeKey": "v1",
                "subject": "losing-subject",
            },
        )
        if accepted.fact.fact_id == ignored.fact.fact_id:
            pytest.fail("Fixtures were not competing immutable primary captures")
        checkpoints.write_candidate(
            baseline_identity=baseline_a,
            run_id="losing",
            folder_id="keep",
            delta_link="https://graph.test/keep?$deltatoken=loser",
            observed_at=LATER,
        )
        promote_validated_mail_delta(
            catalog,
            source_id=SOURCE,
            validated=validated,
        )
        # Late callbacks retain evidence but cannot change a committed winner.
        loser.record_message(
            run_id="losing",
            kind="delta",
            observed_at=LATER,
            evidence_id=None,
            message={
                "id": "present",
                "parentFolderId": "keep",
                "changeKey": "v0",
                "subject": "late-losing-subject",
            },
        )
        with pytest.raises(RuntimeError, match="displaced"):
            checkpoints.commit("losing")
        if "$deltatoken=new" not in (checkpoints.get_delta_link("keep") or ""):
            pytest.fail("Winning provider cursor was not committed")
        ledger = AcquisitionHandoffStore(catalog)
        released = ledger.list_release_entries(
            SOURCE,
            AcquisitionStream.OUTLOOK_MAIL,
            after_seq=0,
            limit=100,
        )
        messages = [
            f
            for entry in released
            for f in ledger.load_release_facts(entry["release_entry_seq"])
            if f.resource_kind == "message" and f.resource_identity == "present"
        ]
        if (
            len(messages) != 1
            or messages[0].fact_id != accepted.fact.fact_id
            or messages[0].run_id != "current"
        ):
            pytest.fail("A losing capture suppressed B's already-winning v2 release")
        with catalog.Session() as session:
            current = session.scalar(
                select(MessageRecord).filter_by(
                    source_id=SOURCE,
                    message_id="present",
                )
            )
            if current is None or current.subject != "winning-subject":
                pytest.fail(
                    "Winning authority cursor left losing primary projection current"
                )
    finally:
        catalog.close()


@pytest.mark.parametrize("loser_when", [CURRENT, LATER, "2026-10-03T00:00:00+00:00"])
def test_losing_folder_delta_cannot_suppress_winning_scoped_removal(
    tmp_path, loser_when
):
    """B removes F, A later writes positive metadata but must lose mailbox CAS."""
    catalog = _catalog(tmp_path)
    try:
        provider = OutlookMailStore(
            catalog,
            source_id=SOURCE,
            spider_name="outlook_folder_delta",
        )
        message_checkpoints = OutlookDeltaCheckpointStore(catalog, SOURCE)
        _folder(provider, "gone-folder", run_id="seed", when=CURRENT)
        message_checkpoints.write_candidate(
            baseline_identity=message_checkpoints.get_delta_start("gone-folder")[1],
            run_id="seed",
            folder_id="gone-folder",
            delta_link="https://graph.test/gone-folder?$deltatoken=old",
            observed_at=CURRENT,
        )
        message_checkpoints.commit("seed")
        independent = OutlookMailStore(catalog, source_id=SOURCE)
        _folder(independent, "unrelated", run_id="seed", when=CURRENT)
        message_checkpoints.write_candidate(
            baseline_identity=message_checkpoints.get_delta_start("unrelated")[1],
            run_id="unrelated",
            folder_id="unrelated",
            delta_link="unchanged",
            observed_at=CURRENT,
        )
        message_checkpoints.commit("unrelated")
        folders = OutlookFolderDeltaCheckpointStore(catalog, SOURCE)
        folders.write_candidate(
            baseline_identity=folders.get_delta_start()[1],
            run_id="seed",
            delta_link="folder-cursor-X",
            observed_at=CURRENT,
        )
        folders.commit("seed")
        _, winner_origin = folders.get_delta_start()
        provider.mark_folder_removed(
            folder_id="gone-folder",
            run_id="winner",
            observed_at=LATER,
            evidence_id=None,
            reason="deleted",
        )
        folders.write_candidate(
            baseline_identity=winner_origin,
            run_id="winner",
            delta_link="folder-cursor-Y",
            observed_at=LATER,
        )
        _folder(provider, "gone-folder", run_id="loser", when=loser_when)
        folders.write_candidate(
            baseline_identity=winner_origin,
            run_id="loser",
            delta_link="folder-cursor-Z",
            observed_at="2026-10-03T00:00:00+00:00",
        )
        folders.commit("winner")
        _folder(
            provider, "gone-folder", run_id="loser", when="2026-10-04T00:00:00+00:00"
        )
        with pytest.raises(RuntimeError, match="displaced"):
            folders.commit("loser")
        if folders.get_delta_link() != "folder-cursor-Y":
            pytest.fail("Winning mailbox cursor did not commit")
        if provider.folder_presence(folder_id="gone-folder") is not False:
            pytest.fail("Losing folder metadata suppressed winning deletion")
        if message_checkpoints.get_delta_link("gone-folder") is not None:
            pytest.fail("Winning deletion failed to invalidate folder message cursor")
        if (
            message_checkpoints.get_delta_link("unrelated") != "unchanged"
            or independent.folder_presence(folder_id="unrelated") is not True
        ):
            pytest.fail("Folder winner changed an unrelated scope")
        ledger = AcquisitionHandoffStore(catalog)
        released = ledger.list_release_entries(
            SOURCE,
            AcquisitionStream.OUTLOOK_MAIL,
            after_seq=0,
            limit=100,
        )
        reasons = [
            (f.transition_reason, f.run_id)
            for entry in released
            for f in ledger.load_release_facts(entry["release_entry_seq"])
            if f.resource_kind == "mail_folder" and f.resource_identity == "gone-folder"
        ]
        if ("folder_delta_removed", "winner") not in reasons:
            pytest.fail("Winning folder deletion was absent from A2 release")
    finally:
        catalog.close()
