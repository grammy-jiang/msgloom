"""Defer folder presence authority until its cursor transaction commits."""

from sqlalchemy import delete, select

from message_ingest.acquisition.handoff import AcquisitionFactKind as Kind
from message_ingest.catalog.models.microsoft.outlook.email import (
    DeltaCheckpoint,
    DeltaCheckpointCandidate,
    MailFolderPresence,
    MailFolderSighting,
)

from ._email_handoff import MailFactWriter, is_stale


def mark_folder_removed(
    store,
    *,
    folder_id,
    run_id,
    observed_at,
    evidence_id,
    reason,
):
    """Stage exact folder control and transition facts without authority."""
    with store.catalog.writer_session() as session:
        presence = session.scalar(
            select(MailFolderPresence).filter_by(
                source_id=store.source_id,
                folder_id=folder_id,
            )
        )
        stale = is_stale(observed_at, presence.latest_observed_at if presence else None)
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
            authority=True,
            reason="folder_delta_removed",
        )
        return outcome


def apply_folder_transitions(session, source_id, facts):
    """
    Apply only winning scoped presence transitions in the checkpoint
    transaction.
    """
    for fact in facts:
        if (
            fact.resource_kind != "mail_folder"
            or fact.component_kind != "folder_presence"
            or fact.transition_reason
            not in {"folder_delta_removed", "folder_delta_present"}
        ):
            continue
        presence = session.scalar(
            select(MailFolderPresence).filter_by(
                source_id=source_id,
                folder_id=fact.resource_identity,
            )
        )
        if presence is None:
            presence = MailFolderPresence(
                source_id=source_id,
                folder_id=fact.resource_identity,
            )
            session.add(presence)
        present = fact.transition_reason == "folder_delta_present"
        presence.is_present = present
        presence.removed_reason = None if present else "folder_delta_removed"
        presence.latest_run_id = fact.run_id
        presence.latest_observed_at = fact.provider_observed_at
        presence.latest_evidence_id = fact.evidence_id
        if present:
            continue
        for model in (DeltaCheckpoint, DeltaCheckpointCandidate):
            session.execute(
                delete(model).where(
                    model.source_id == source_id,
                    model.folder_id == fact.resource_identity,
                )
            )


def stage_folder_present(
    store, session, *, folder_id, run_id, observed_at, evidence_id
):
    """Keep positive folder presence pending until its cursor wins."""
    MailFactWriter(store.catalog, store.source_id, store.spider_name).stage(
        session,
        run_id=run_id,
        resource_id=folder_id,
        resource_kind="mail_folder",
        kind=Kind.SCOPED_STATE_TRANSITION,
        component="folder_presence",
        scope_id=folder_id,
        state={"is_present": True},
        evidence_id=evidence_id,
        observed_at=observed_at,
        authority=True,
        reason="folder_delta_present",
    )


def mark_folder_present_in_session(
    self,
    session,
    *,
    folder_id: str,
    run_id: str | None,
    observed_at: str,
    evidence_id: str | None,
) -> None:
    """Record folder presence and this run's inventory sighting."""
    if self.spider_name == "outlook_folder_delta":
        stage_folder_present(
            self,
            session,
            folder_id=folder_id,
            run_id=run_id,
            observed_at=observed_at,
            evidence_id=evidence_id,
        )
        return
    presence = session.scalar(
        select(MailFolderPresence).filter_by(
            source_id=self.source_id,
            folder_id=folder_id,
        )
    )
    if presence is None:
        session.add(
            MailFolderPresence(
                source_id=self.source_id,
                folder_id=folder_id,
                is_present=True,
                removed_reason=None,
                latest_run_id=run_id,
                latest_observed_at=observed_at,
                latest_evidence_id=evidence_id,
            )
        )
    elif observed_at >= presence.latest_observed_at:
        presence.is_present = True
        presence.removed_reason = None
        presence.latest_run_id = run_id
        presence.latest_observed_at = observed_at
        presence.latest_evidence_id = evidence_id
    if run_id:
        existing = session.scalar(
            select(MailFolderSighting.id).filter_by(
                source_id=self.source_id,
                run_id=run_id,
                folder_id=folder_id,
            )
        )
        if existing is None:
            session.add(
                MailFolderSighting(
                    source_id=self.source_id,
                    run_id=run_id,
                    folder_id=folder_id,
                    observed_at=observed_at,
                    evidence_id=evidence_id,
                )
            )
