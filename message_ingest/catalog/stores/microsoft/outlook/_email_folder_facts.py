"""Folder-delta tombstones remain scoped and pending authority publication."""

from sqlalchemy import delete, select

from message_ingest.acquisition.handoff import AcquisitionFactKind as Kind
from message_ingest.catalog.models.microsoft.outlook.email import (
    DeltaCheckpoint,
    DeltaCheckpointCandidate,
    MailFolderPresence,
)

from ._email_handoff import MailFactWriter, MailPersistenceOutcome, is_stale


def mark_folder_removed(
    store,
    *,
    folder_id: str,
    run_id: str | None,
    observed_at: str,
    evidence_id: str | None,
    reason: str | None,
) -> MailPersistenceOutcome:
    """
    Stage control and transition facts with presence/cursor mutation.

    No release is created here. Task 9's folder-checkpoint owner must select
    only the winning staged facts inside its authority transaction.
    """
    with store.catalog.writer_session() as session:
        presence = session.scalar(
            select(MailFolderPresence).filter_by(
                source_id=store.source_id,
                folder_id=folder_id,
            )
        )
        stale = is_stale(observed_at, presence.latest_observed_at if presence else None)
        equivalent = bool(presence and not presence.is_present)
        if not stale:
            store._set_folder_presence(
                session,
                folder_id=folder_id,
                is_present=False,
                reason=reason or "folder_delta_removed",
                run_id=run_id or "",
                observed_at=observed_at,
                evidence_id=evidence_id,
            )
            for model in (DeltaCheckpoint, DeltaCheckpointCandidate):
                session.execute(
                    delete(model).where(
                        model.source_id == store.source_id,
                        model.folder_id == folder_id,
                    )
                )
        writer = MailFactWriter(store.catalog, store.source_id, store.spider_name)
        outcome = writer.stage(
            session,
            run_id=run_id,
            resource_id=folder_id,
            resource_kind="mail_folder",
            kind=Kind.CONTROL_CONTEXT,
            state={"is_present": False},
            evidence_id=evidence_id,
            observed_at=observed_at,
            stale=stale,
            equivalent=equivalent,
            authority=True,
        )
        writer.stage(
            session,
            run_id=run_id,
            resource_id=folder_id,
            resource_kind="mail_folder",
            kind=Kind.SCOPED_STATE_TRANSITION,
            component="folder_presence",
            scope_id=folder_id,
            state={"is_present": False},
            evidence_id=evidence_id,
            observed_at=observed_at,
            stale=stale,
            equivalent=equivalent,
            authority=True,
            reason="folder_delta_removed",
        )
        return outcome
