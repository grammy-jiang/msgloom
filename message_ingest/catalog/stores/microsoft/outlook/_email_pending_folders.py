"""Stage folder-delta metadata and presence as one owned observation."""

from sqlalchemy import select

from message_ingest.acquisition.handoff import AcquisitionFactKind as Kind
from message_ingest.catalog.models.microsoft.outlook.email import (
    MailFolderPresence,
    MailFolderRecord,
)

from ._email_handoff import MailPersistenceOutcome, is_stale
from ._email_observations import (
    accepted_is_newer,
    capture_key,
    head,
    load_fact,
    require_open,
    retain,
    verify_resource,
)

FOLDER_FIELDS = {
    "displayName": "display_name",
    "parentFolderId": "parent_folder_id",
    "childFolderCount": "child_folder_count",
    "totalItemCount": "total_item_count",
    "unreadItemCount": "unread_item_count",
    "isHidden": "is_hidden",
}


def stage_folder(store, session, *, folder, run_id, observed_at, evidence_id, present):
    """Retain competing cursor inputs without publishing their metadata."""
    from message_ingest.acquisition.handoff import AcquisitionStream, EffectiveStateKey

    if not run_id:
        raise ValueError("Folder delta requires original run")
    key = EffectiveStateKey(
        source_id=store.source_id,
        stream=AcquisitionStream.OUTLOOK_MAIL,
        resource_kind="mail_folder",
        resource_identity=folder["id"],
    ).digest
    previous = head(
        session,
        store.source_id,
        run_id,
        "folder_delta",
        store.source_id,
        "mail_folder",
        folder["id"],
        effective_key=key,
    )
    capture = capture_key(folder, present, observed_at, evidence_id)
    if previous is not None and previous.capture_key == capture:
        fact = load_fact(session, previous)
        from message_ingest.acquisition.handoff import StorageRelation

        return MailPersistenceOutcome(fact, StorageRelation(fact.storage_relation))
    require_open(session, store.source_id, run_id, "folder_delta")
    verify_resource(session, store.source_id, evidence_id, folder)
    stale = previous is not None and is_stale(
        observed_at, load_fact(session, previous).provider_observed_at
    )
    for model in (MailFolderRecord, MailFolderPresence):
        record = session.scalar(
            select(model).filter_by(source_id=store.source_id, folder_id=folder["id"])
        )
        if record is not None:
            stale |= accepted_is_newer(
                session,
                key,
                "folder_delta",
                store.source_id,
                observed_at,
                record.latest_observed_at,
            )
    writer = store._facts()
    context = writer.stage(
        session,
        run_id=run_id,
        resource_id=folder["id"],
        resource_kind="mail_folder",
        kind=Kind.CONTROL_CONTEXT,
        state={"folder": folder, "is_present": True}
        if present
        else {"is_present": False},
        evidence_id=evidence_id,
        observed_at=observed_at,
        authority=True,
        stale=stale,
    )
    transition = writer.stage(
        session,
        run_id=run_id,
        resource_id=folder["id"],
        resource_kind="mail_folder",
        kind=Kind.SCOPED_STATE_TRANSITION,
        component="folder_presence",
        scope_id=folder["id"],
        state={"is_present": present},
        evidence_id=evidence_id,
        observed_at=observed_at,
        authority=True,
        stale=stale,
        reason="folder_delta_present" if present else "folder_delta_removed",
    )
    for outcome in (context, transition):
        retain(
            session,
            outcome.fact,
            authority="folder_delta",
            scope=store.source_id,
            capture=capture,
            payload={
                "resource": folder,
                "present": present,
                "projection": {
                    col: folder.get(field) for field, col in FOLDER_FIELDS.items()
                },
            },
        )
    return context
