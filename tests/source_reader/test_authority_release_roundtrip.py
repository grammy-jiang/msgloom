"""Join real Mail authority promotion to immutable public Reader results."""

import pytest

from message_ingest.catalog import Catalog
from message_ingest.catalog.stores.microsoft.outlook.email import OutlookMailStore
from message_ingest.sync.microsoft.outlook.email.checkpoints import (
    OutlookDeltaCheckpointStore,
    OutlookFolderDeltaCheckpointStore,
)
from message_ingest.sync.microsoft.outlook.email.promotion import (
    ValidatedMailDeltaRun,
    promote_validated_mail_delta,
)
from tests.source_reader.authority_release_helpers import (
    CURRENT,
    FOLDER,
    LATER,
    MESSAGE,
    OLD,
    entries,
    only,
    page_bytes,
    read_entries,
)
from tests.source_reader.release_mail_helpers import mail_catalog as _mail_catalog
from tests.source_reader.release_nonmail_helpers import SOURCE, save_evidence

mail_catalog = _mail_catalog


def test_message_delta_authority_to_public_reader(mail_catalog):
    """Pin resources, contexts and mailbox removals across replay and updates."""
    saved = mail_catalog
    gone = {**MESSAGE, "id": "gone"}
    old_page = {"value": [MESSAGE, gone]}
    folder_page = {"value": [FOLDER]}
    save_evidence(saved, "baseline", old_page)
    save_evidence(saved, "folders", folder_page)
    catalog = Catalog(f"sqlite:///{saved['database']}")
    store = OutlookMailStore(catalog, source_id=SOURCE)
    checkpoints = OutlookDeltaCheckpointStore(catalog, SOURCE)
    try:
        for raw in (MESSAGE, gone):
            store.record_message(
                run_id="baseline",
                message=raw,
                kind="delta",
                evidence_id="baseline",
                observed_at=OLD,
            )
        store.upsert_folder(
            run_id="current",
            folder=FOLDER,
            evidence_id="folders",
            observed_at=CURRENT,
        )
        # Change the provider version so the authority primary owns this page.
        current = {**MESSAGE, "changeKey": "v2"}
        page = {"value": [current]}
        save_evidence(saved, "current-message", page)
        store.record_message(
            run_id="current",
            message=current,
            kind="delta",
            evidence_id="current-message",
            observed_at=CURRENT,
        )
        store.record_message_sighting(
            run_id="current",
            message_id="present",
            observed_at=CURRENT,
            evidence_id="current-message",
        )
        store.write_folder_snapshot_candidate(
            run_id="current",
            observed_at=CURRENT,
            evidence_id="folders",
        )
        store.write_message_presence_candidate(
            run_id="current",
            observed_at=CURRENT,
            evidence_id="current-message",
        )
        checkpoints.write_candidate(
            run_id="current",
            folder_id="inbox",
            delta_link="https://graph.test/new",
            observed_at=CURRENT,
            evidence_id="current-message",
        )
        validated = ValidatedMailDeltaRun(
            run_id="current",
            expected_folder_ids=frozenset({"inbox"}),
            reconcile_messages=True,
            candidate_folder_ids=frozenset({"inbox"}),
        )
        if entries(catalog):
            pytest.fail("Staged message facts published authority before promotion")
        promote_validated_mail_delta(catalog, source_id=SOURCE, validated=validated)
        rows = entries(catalog)
        before = read_entries(saved, rows)
        _, primary, primary_bytes = only(before, "resource", "present")
        if primary.selection is None:
            pytest.fail("Promoted message has no public selection")
        if (
            primary.selection.record.source_bytes is None
            or primary.selection.record.subject != MESSAGE["subject"]
            or primary_bytes != (page_bytes(page),)
            or primary.selection.record.source_bytes.reference
            != "a1-response:current-message"
        ):
            pytest.fail("Promoted primary lost exact observed fields or evidence")
        _, context, context_bytes = only(before, "context", "inbox")
        if context.selection is not None or len(context.contexts) != 1:
            pytest.fail("Folder context fabricated a message selection")
        if context_bytes != (page_bytes(folder_page),):
            pytest.fail("Folder context lost its exact evidence bytes")
        _, removed, removed_bytes = only(before, "transition", "gone")
        if removed.selection is not None or len(removed.transitions) != 1:
            pytest.fail("Mailbox removal fabricated a primary selection")
        transition = removed.transitions[0]
        if (
            transition.scope_kind != "mailbox"
            or transition.scope_identity != SOURCE
            or transition.resource_identity != "gone"
            or transition.reason != "not_in_complete_reconciliation"
            or removed_bytes != (page_bytes(page),)
        ):
            pytest.fail("Mailbox removal lost scope, reason or completion evidence")
        promote_validated_mail_delta(catalog, source_id=SOURCE, validated=validated)
        if entries(catalog) != rows:
            pytest.fail("Replay changed release group or entry identities")
        latest = {**MESSAGE, "changeKey": "v3", "subject": "Advanced subject"}
        save_evidence(saved, "latest", {"value": [latest, gone]})
        save_evidence(saved, "latest-folder", {**FOLDER, "displayName": "Advanced"})
        for raw in (latest, gone):
            store.record_message(
                run_id="later",
                message=raw,
                kind="delta",
                evidence_id="latest",
                observed_at=LATER,
            )
        store.upsert_folder(
            run_id="later",
            folder={**FOLDER, "displayName": "Advanced"},
            evidence_id="latest-folder",
            observed_at=LATER,
        )
        current_state = store.get_message_state(message_id="present")
        if current_state is None or current_state["latest_evidence_id"] != "latest":
            pytest.fail("Mutable message projection did not advance")
        if store.message_presence(message_id="gone") is not True:
            pytest.fail("Later observation did not restore mutable message presence")
        if read_entries(saved, rows) != before:
            pytest.fail("Mutable advancement changed an old release anchor")
    finally:
        catalog.close()


@pytest.mark.parametrize("removed", [False, True], ids=["positive", "removal"])
def test_folder_delta_authority_to_public_reader(mail_catalog, removed):
    """Release exact folder context and scope only after cursor commit."""
    saved = mail_catalog
    raw = {"id": "inbox", "@removed": {"reason": "deleted"}} if removed else FOLDER
    page = {"value": [raw]}
    save_evidence(saved, "folder-page", page)
    save_evidence(saved, "baseline-mail", {"value": [MESSAGE]})
    catalog = Catalog(f"sqlite:///{saved['database']}")
    baseline = OutlookMailStore(catalog, source_id=SOURCE)
    store = OutlookMailStore(
        catalog, source_id=SOURCE, spider_name="outlook_folder_delta"
    )
    checkpoints = OutlookFolderDeltaCheckpointStore(catalog, SOURCE)
    try:
        baseline.record_message(
            run_id="baseline",
            message=MESSAGE,
            kind="delta",
            evidence_id="baseline-mail",
            observed_at=OLD,
        )
        if removed:
            store.mark_folder_removed(
                run_id="folder-run",
                folder_id="inbox",
                reason="deleted",
                evidence_id="folder-page",
                observed_at=CURRENT,
            )
        else:
            store.upsert_folder(
                run_id="folder-run",
                folder=raw,
                evidence_id="folder-page",
                observed_at=CURRENT,
            )
        checkpoints.write_candidate(
            run_id="folder-run",
            delta_link="https://graph.test/folders",
            observed_at=CURRENT,
            evidence_id="folder-page",
        )
        if entries(catalog):
            pytest.fail("Staged folder facts published authority before commit")
        checkpoints.commit("folder-run")
        if store.folder_presence(folder_id="inbox") is not (not removed):
            pytest.fail("Folder commit did not apply its presence decision")
        rows = entries(catalog)
        before = read_entries(saved, rows)
        if len(before) != 2:
            pytest.fail("Folder authority did not publish exactly its two impacts")
        _, context, context_bytes = only(before, "context", "inbox")
        _, state, state_bytes = only(before, "transition", "inbox")
        if context.selection is not None or state.selection is not None:
            pytest.fail("Folder authority fabricated a message selection")
        if len(context.contexts) != 1 or len(state.transitions) != 1:
            pytest.fail("Folder authority lost its context or transition")
        transition = state.transitions[0]
        reason = "folder_delta_removed" if removed else "folder_delta_present"
        if (
            transition.resource_kind != "mail_folder"
            or transition.resource_identity != "inbox"
            or transition.scope_kind != "mail_folder"
            or transition.scope_identity != "inbox"
            or transition.reason != reason
            or context_bytes != (page_bytes(page),)
            or state_bytes != (page_bytes(page),)
        ):
            pytest.fail("Folder authority lost identity, scope, reason or evidence")
        if baseline.message_presence(message_id="present") is not True:
            pytest.fail("Folder authority fabricated mailbox-wide message deletion")
        checkpoints.commit("folder-run")
        if entries(catalog) != rows:
            pytest.fail("Folder replay changed group or entry identities")
        advanced = {**FOLDER, "displayName": "Advanced folder"}
        save_evidence(saved, "advanced-folder", {"value": [advanced]})
        baseline.upsert_folder(
            run_id="later",
            folder=advanced,
            evidence_id="advanced-folder",
            observed_at=LATER,
        )
        if baseline.folder_presence(folder_id="inbox") is not True:
            pytest.fail("Later folder observation did not advance mutable presence")
        if read_entries(saved, rows) != before:
            pytest.fail("Mutable folder advancement changed old release bytes")
    finally:
        catalog.close()
